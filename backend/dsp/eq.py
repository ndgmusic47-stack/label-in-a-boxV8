from pydub import AudioSegment
import numpy as np

def apply_eq(audio: AudioSegment, low_gain_db=0.0, mid_gain_db=0.0, high_gain_db=0.0):
    """
    Apply simple 3-band EQ to the audio using FFT domain gain adjustments.
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # FFT
    fft = np.fft.rfft(samples)
    freqs = np.fft.rfftfreq(len(samples), d=1.0 / audio.frame_rate)

    # Convert dB to linear
    low_gain = 10 ** (low_gain_db / 20)
    mid_gain = 10 ** (mid_gain_db / 20)
    high_gain = 10 ** (high_gain_db / 20)

    # Apply gains by frequency region
    low_region = freqs < 250
    mid_region = (freqs >= 250) & (freqs < 4000)
    high_region = freqs >= 4000

    fft[low_region] *= low_gain
    fft[mid_region] *= mid_gain
    fft[high_region] *= high_gain

    # Inverse FFT
    filtered = np.fft.irfft(fft)
    filtered_samples = filtered.astype(np.int16).tobytes()

    return audio._spawn(filtered_samples)
