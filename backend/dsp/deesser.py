from pydub import AudioSegment
import numpy as np


def apply_deesser(audio: AudioSegment, threshold_db: float = -20.0, reduction_db: float = -6.0):
    """
    Simple FFT-based de-esser that reduces harsh sibilance (5–10 kHz).
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # FFT
    fft = np.fft.rfft(samples)
    freqs = np.fft.rfftfreq(len(samples), d=1.0 / audio.frame_rate)

    # Convert dB threshold + reduction
    threshold = 10 ** (threshold_db / 20)
    reduction = 10 ** (reduction_db / 20)

    # Identify sibilance region (5–10 kHz)
    s_region = (freqs >= 5000) & (freqs <= 10000)

    # Apply reduction where amplitude exceeds threshold
    mask = np.abs(fft[s_region]) > threshold
    fft[s_region][mask] *= reduction

    # iFFT
    filtered = np.fft.irfft(fft)
    filtered_samples = filtered.astype(np.int16).tobytes()

    return audio._spawn(filtered_samples)
