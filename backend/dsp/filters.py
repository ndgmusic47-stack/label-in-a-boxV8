from pydub import AudioSegment
import numpy as np


def high_pass_filter(audio: AudioSegment, cutoff_hz: int = 120):
    """
    Apply a simple high-pass filter to remove low-end rumble.
    """
    # Convert to raw samples
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # FFT
    fft = np.fft.rfft(samples)

    # Frequency resolution
    freqs = np.fft.rfftfreq(len(samples), d=1.0 / audio.frame_rate)

    # Zero out frequencies below cutoff
    fft[freqs < cutoff_hz] = 0

    # Inverse FFT
    filtered = np.fft.irfft(fft)

    # Convert back to AudioSegment
    filtered_samples = filtered.astype(np.int16).tobytes()

    return audio._spawn(filtered_samples)
