from pydub import AudioSegment
import numpy as np


def apply_compression(
    audio: AudioSegment,
    threshold_db: float = -18.0,
    ratio: float = 4.0,
    attack_ms: float = 5.0,
    release_ms: float = 50.0
):
    """
    Apply simple dynamic range compression to audio.
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    sr = audio.frame_rate

    # Convert dB threshold to linear
    threshold = 10 ** (threshold_db / 20)

    # Envelope follower parameters
    attack_coeff = np.exp(-1.0 / (sr * (attack_ms / 1000.0)))
    release_coeff = np.exp(-1.0 / (sr * (release_ms / 1000.0)))

    envelope = 0.0
    gain = np.ones_like(samples)

    for i, sample in enumerate(samples):
        rectified = abs(sample)

        # Envelope detection
        if rectified > envelope:
            envelope = attack_coeff * envelope + (1 - attack_coeff) * rectified
        else:
            envelope = release_coeff * envelope + (1 - release_coeff) * rectified

        # Compression gain calculation
        if envelope > threshold:
            over = envelope / threshold
            gain_reduction = over ** (1 - 1 / ratio)
            gain[i] = 1 / gain_reduction
        else:
            gain[i] = 1.0

    # Apply gain
    compressed = samples * gain
    compressed = np.clip(compressed, -32768, 32767)

    return audio._spawn(compressed.astype(np.int16).tobytes())
