from pydub import AudioSegment
import numpy as np


def apply_limiter(audio: AudioSegment, ceiling_db: float = -1.0):
    """
    Simple peak limiter that clamps peaks above the ceiling.
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # Convert ceiling from dBFS to linear
    ceiling = 10 ** (ceiling_db / 20)

    # Find peak amplitude
    peak = np.max(np.abs(samples))
    if peak == 0:
        return audio  # silent audio

    # If audio exceeds ceiling, scale it down
    if peak > ceiling * 32767:
        reduction = (ceiling * 32767) / peak
        samples = samples * reduction

    # Clip to int16 range
    samples = np.clip(samples, -32768, 32767)

    return audio._spawn(samples.astype(np.int16).tobytes())
