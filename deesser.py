from pydub import AudioSegment
import numpy as np


def apply_deesser(audio: AudioSegment, freq_start: int = 6000, freq_end: int = 9000, threshold: float = -25.0):
    """
    De-esser with improved band-pass detection (peak + RMS combined) in 6-9 kHz range.
    
    Parameters:
    - freq_start: 6000 Hz (start of detection band)
    - freq_end: 9000 Hz (end of detection band)
    - threshold: -25 dB (detection threshold)
    - Reduction: 3-5 dB more precisely when triggered
    - Release stage: 20-30ms for smooth operation
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    sr = audio.frame_rate

    # Normalize samples to [-1, 1] range for processing
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples_norm = samples / max_val
    else:
        samples_norm = samples
        return audio  # silent audio

    # Convert threshold to linear (normalized)
    threshold_linear = 10 ** (threshold / 20)
    
    # Reduction amount: 3-5 dB more precisely
    reduction_db = -4.0  # Average reduction in the 3-5 dB range
    reduction_linear = 10 ** (reduction_db / 20)
    
    # Release stage: 25ms (20-30ms range)
    release_ms = 25.0
    release_coeff = np.exp(-1.0 / (sr * (release_ms / 1000.0)))

    # Process in overlapping windows for smoother operation
    window_size = int(sr * 0.01)  # 10ms windows
    hop_size = window_size // 4  # 75% overlap
    if window_size < 1:
        window_size = 1
    if hop_size < 1:
        hop_size = 1

    # Create output array
    output = samples_norm.copy()
    gain_reduction = np.ones_like(samples_norm)
    detected_level = 0.0  # For release stage tracking

    # Process in windows
    for i in range(0, len(samples_norm) - window_size, hop_size):
        window = samples_norm[i:i + window_size]
        
        # FFT of window
        fft_window = np.fft.rfft(window)
        freqs_window = np.fft.rfftfreq(len(window), d=1.0 / sr)
        
        # Band-pass filter: isolate 6-9 kHz region
        band_mask = (freqs_window >= freq_start) & (freqs_window <= freq_end)
        
        # Extract band-pass region
        band_fft = fft_window.copy()
        band_fft[~band_mask] = 0
        band_signal = np.fft.irfft(band_fft)
        
        # Improved detection: Peak + RMS combined
        band_rms = np.sqrt(np.mean(band_signal ** 2))
        band_peak = np.max(np.abs(band_signal))
        
        # Combine peak and RMS for more accurate detection
        # Peak gives transient response, RMS gives sustained level
        combined_level = 0.6 * band_rms + 0.4 * band_peak
        
        # Apply release stage: gradually reduce detected level
        if combined_level > detected_level:
            detected_level = combined_level
        else:
            detected_level = release_coeff * detected_level + (1 - release_coeff) * combined_level
        
        # If combined level exceeds threshold, apply reduction
        if detected_level > threshold_linear:
            # Calculate reduction amount (proportional to how much over threshold)
            over_threshold = detected_level / threshold_linear
            # More precise reduction curve (3-5 dB range)
            reduction_factor = 1.0 - (1.0 - reduction_linear) * min(1.0, (over_threshold - 1.0) * 0.6)
            
            # Apply reduction to this window
            for j in range(i, min(i + window_size, len(gain_reduction))):
                gain_reduction[j] = min(gain_reduction[j], reduction_factor)

    # Smooth gain reduction to avoid artifacts
    # Simple moving average smoothing
    smooth_window = int(sr * 0.001)  # 1ms smoothing
    if smooth_window > 1:
        smoothed_gain = np.zeros_like(gain_reduction)
        for i in range(len(gain_reduction)):
            start_idx = max(0, i - smooth_window // 2)
            end_idx = min(len(gain_reduction), i + smooth_window // 2)
            smoothed_gain[i] = np.mean(gain_reduction[start_idx:end_idx])
        gain_reduction = smoothed_gain

    # Apply gain reduction
    output = samples_norm * gain_reduction
    
    # Scale back to original range
    if max_val > 0:
        output = output * max_val
    
    # Clip to int16 range
    output = np.clip(output, -32768, 32767)

    return audio._spawn(output.astype(np.int16).tobytes())
