from pydub import AudioSegment
from pydub.effects import normalize, strip_silence
import numpy as np

from .filters import high_pass_filter
from .eq import apply_eq
from .compressor import apply_compression
from .deesser import apply_deesser
from .limiter import apply_limiter


def soft_clip_saturation(audio: AudioSegment, drive=1.0):
    """
    Add subtle harmonic warmth using soft clipping without distortion.
    
    Parameters:
    - drive: 1.015 for micro-saturation (subtle warmth)
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    samples *= drive
    samples = np.tanh(samples / 32768.0) * 32768.0
    return audio._spawn(samples.astype(audio.array_type))


def process_vocal(vocal: AudioSegment) -> AudioSegment:
    """
    Full DSP pipeline for modern vocal processing.
    
    Processing chain:
    0. Silence trimming - removes trailing noise before processing
    1. High-pass filter at 80 Hz - removes low-end rumble and sub-bass
    2. EQ shaping - modern rap/soul vocal curve for clarity and presence
    3. Micro-saturation - adds subtle harmonic warmth
    4. Compression - 4:1 ratio, -18dB threshold, 10ms attack, 80ms release
    5. De-essing - 6-9 kHz detection, -25dB threshold to tame sibilance
    6. Limiter - -1.0 dB ceiling to prevent clipping
    7. Final normalization - ensures consistent output level with headroom
    """
    # Stage 0: Silence trimming
    # Keeps mixes tight and removes trailing noise
    vocal = strip_silence(vocal, silence_len=800, silence_thresh=-45)
    
    # Stage 1: High-pass filter at 80 Hz
    # Removes low-end rumble and sub-bass that can muddy the mix
    vocal = high_pass_filter(vocal, cutoff=80)
    
    # Stage 2: Modern EQ curve
    # Shapes the frequency response for modern rap/soul vocals
    vocal = apply_eq(vocal)
    
    # Stage 3: Micro-saturation for warmth
    # Adds subtle harmonic warmth without distortion
    vocal = soft_clip_saturation(vocal, drive=1.015)
    
    # Stage 4: Compression
    # Controls dynamics with 4:1 ratio, -18dB threshold, 10ms attack, 80ms release
    vocal = apply_compression(
        vocal,
        threshold=-18.0,
        ratio=4.0,
        attack=10,
        release=80
    )
    
    # Stage 5: De-essing
    # Reduces harsh sibilance in the 6-9 kHz range with -25dB threshold
    vocal = apply_deesser(vocal, freq_start=6000, freq_end=9000, threshold=-25)
    
    # Stage 6: Limiter
    # Prevents clipping with -1.0 dB ceiling
    final_mix = apply_limiter(vocal, ceiling=-1.0)
    
    # Stage 7: Final output normalization
    # Ensures consistent output level with headroom
    final_mix = normalize(final_mix)
    
    # Reduce by 0.8 dB to ensure headroom
    samples = np.array(final_mix.get_array_of_samples()).astype(np.float32)
    headroom_reduction = 10 ** (-0.8 / 20)  # Convert -0.8 dB to linear
    samples = samples * headroom_reduction
    final_mix = final_mix._spawn(samples.astype(final_mix.array_type))
    
    return final_mix
