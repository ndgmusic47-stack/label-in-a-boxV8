from pydub import AudioSegment
import numpy as np


def apply_compression(
    audio: AudioSegment,
    threshold: float = -18.0,
    ratio: float = 4.0,
    attack: float = 10.0,
    release: float = 80.0
):
    """
    Apply dynamic range compression with RMS detection and soft knee.
    
    Parameters:
    - threshold: -18 dB (compression threshold)
    - ratio: 4:1 (compression ratio)
    - attack: 10 ms (attack time)
    - release: 80 ms (release time)
    - Uses RMS detection for more musical compression
    - Soft knee for smoother transitions
    - Harmonic compensation: +1.0 dB at 3 kHz to maintain presence after compression
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    sr = audio.frame_rate

    # Normalize samples to [-1, 1] range
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples_norm = samples / max_val
    else:
        samples_norm = samples

    # Convert dB threshold to linear (normalized)
    threshold_linear = 10 ** (threshold / 20)

    # RMS window size (approximately 10ms for RMS averaging)
    rms_window_size = int(sr * 0.01)  # 10ms window
    if rms_window_size < 1:
        rms_window_size = 1

    # Envelope follower parameters
    attack_coeff = np.exp(-1.0 / (sr * (attack / 1000.0)))
    release_coeff = np.exp(-1.0 / (sr * (release / 1000.0)))

    # Soft knee width (in dB)
    knee_width_db = 3.0
    knee_width_linear = 10 ** (knee_width_db / 20)

    # Calculate RMS for each sample using sliding window
    rms_values = np.zeros_like(samples_norm)
    for i in range(len(samples_norm)):
        start_idx = max(0, i - rms_window_size // 2)
        end_idx = min(len(samples_norm), i + rms_window_size // 2)
        window = samples_norm[start_idx:end_idx]
        rms_values[i] = np.sqrt(np.mean(window ** 2))

    # Envelope follower on RMS values
    envelope = 0.0
    gain = np.ones_like(samples_norm)

    for i, rms in enumerate(rms_values):
        # Envelope detection with attack/release
        if rms > envelope:
            envelope = attack_coeff * envelope + (1 - attack_coeff) * rms
        else:
            envelope = release_coeff * envelope + (1 - release_coeff) * rms

        # Soft knee compression
        knee_start = threshold_linear / knee_width_linear
        knee_end = threshold_linear * knee_width_linear

        if envelope < knee_start:
            # Below knee: no compression
            gain[i] = 1.0
        elif envelope < knee_end:
            # In knee region: gradual compression
            over = envelope / knee_start
            knee_ratio = 1.0 + (ratio - 1.0) * ((envelope - knee_start) / (knee_end - knee_start))
            gain_reduction = over ** (1 - 1 / knee_ratio)
            gain[i] = 1.0 / gain_reduction
        else:
            # Above knee: full compression
            over = envelope / threshold_linear
            gain_reduction = over ** (1 - 1 / ratio)
            gain[i] = 1.0 / gain_reduction

    # Apply gain and scale back to original range
    compressed = samples_norm * gain
    if max_val > 0:
        compressed = compressed * max_val
    
    # Harmonic compensation: add +1.0 dB at 3 kHz using single-peaking EQ band
    # Ensures presence is maintained after compression
    compensation_gain_db = 1.0
    compensation_freq = 3000.0
    compensation_q = 2.0
    
    # Apply Hann window before FFT for clean processing
    hann_window = np.hanning(len(compressed))
    windowed_compressed = compressed * hann_window
    
    # FFT
    fft_compressed = np.fft.rfft(windowed_compressed)
    freqs_compressed = np.fft.rfftfreq(len(compressed), d=1.0 / sr)
    
    # Create peaking EQ band at 3 kHz
    gain_linear = 10 ** (compensation_gain_db / 20)
    bandwidth = compensation_freq / compensation_q
    dist = np.abs(freqs_compressed - compensation_freq)
    bell = 1.0 + (gain_linear - 1.0) * np.exp(-(dist ** 2) / (2 * (bandwidth / 2) ** 2))
    
    # Apply EQ
    fft_compressed *= bell
    
    # Inverse FFT
    compensated = np.fft.irfft(fft_compressed)
    
    # Normalize to maintain peak level
    compressed_peak = np.max(np.abs(compressed)) if len(compressed) > 0 else 1.0
    compensated_peak = np.max(np.abs(compensated)) if len(compensated) > 0 else 1.0
    if compensated_peak > 0:
        normalization_factor = compressed_peak / compensated_peak
        compensated = compensated * normalization_factor
    
    # Clip to int16 range
    compensated = np.clip(compensated, -32768, 32767)

    return audio._spawn(compensated.astype(np.int16).tobytes())
