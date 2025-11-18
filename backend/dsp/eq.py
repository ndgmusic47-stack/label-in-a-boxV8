from pydub import AudioSegment
import numpy as np

def apply_eq(audio: AudioSegment):
    """
    Apply modern rap/soul vocal EQ curve using FFT-based bell filters.
    
    EQ points:
    +3 dB @ 150 Hz (warmth)
    -2 dB @ 300 Hz (mud reduction)
    -3 dB @ 500 Hz (nasal reduction)
    +2.5 dB @ 2.5 kHz (presence)
    +4.0 dB @ 8 kHz (air)
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # Apply Hann window before FFT to prevent ringing & phase smearing
    hann_window = np.hanning(len(samples))
    windowed_samples = samples * hann_window

    # FFT
    fft = np.fft.rfft(windowed_samples)
    freqs = np.fft.rfftfreq(len(samples), d=1.0 / audio.frame_rate)

    # Create gain curve (start at 0 dB)
    gain_curve = np.ones_like(freqs, dtype=np.float32)
    
    # Bell filter function: applies gain at center frequency with Q bandwidth
    def apply_bell(center_freq, gain_db, q=1.0):
        """Apply bell-shaped EQ boost/cut at center frequency"""
        gain_linear = 10 ** (gain_db / 20)
        # Bandwidth in Hz
        bandwidth = center_freq / q
        # Distance from center frequency
        dist = np.abs(freqs - center_freq)
        # Bell shape: gain falls off with distance
        # Using a smoother curve for more musical sound
        bell = 1.0 + (gain_linear - 1.0) * np.exp(-(dist ** 2) / (2 * (bandwidth / 2) ** 2))
        return bell
    
    # Apply each EQ point
    # +3 dB @ 150 Hz (warmth) - Q=1.5 for gentle boost
    gain_curve *= apply_bell(150, 3.0, q=1.5)
    
    # -2 dB @ 300 Hz (mud) - Q=2.0 for tighter cut
    gain_curve *= apply_bell(300, -2.0, q=2.0)
    
    # -3 dB @ 500 Hz (nasal) - Q=2.0 for tighter cut
    gain_curve *= apply_bell(500, -3.0, q=2.0)
    
    # +2.5 dB @ 2.5 kHz (presence) - Q=1.5 for gentle boost
    gain_curve *= apply_bell(2500, 2.5, q=1.5)
    
    # +4.0 dB @ 8 kHz (air) - Q=2.0 for focused boost
    gain_curve *= apply_bell(8000, 4.0, q=2.0)
    
    # Apply gain curve to FFT
    fft *= gain_curve

    # Inverse FFT
    filtered = np.fft.irfft(fft)
    
    # Normalize gain after processing to prevent resonance artifacts
    # Calculate normalization factor to maintain original peak level
    original_peak = np.max(np.abs(samples)) if len(samples) > 0 else 1.0
    filtered_peak = np.max(np.abs(filtered)) if len(filtered) > 0 else 1.0
    if filtered_peak > 0:
        normalization_factor = original_peak / filtered_peak
        filtered = filtered * normalization_factor
    
    filtered_samples = filtered.astype(np.int16).tobytes()

    return audio._spawn(filtered_samples)
