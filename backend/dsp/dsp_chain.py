from pydub import AudioSegment

from .filters import high_pass_filter
from .eq import apply_eq
from .compressor import apply_compression
from .deesser import apply_deesser
from .limiter import apply_limiter


def process_vocal(
    audio: AudioSegment,
    hp_cutoff=120,
    low_gain_db=0.0,
    mid_gain_db=0.0,
    high_gain_db=0.0,
    threshold_db=-18.0,
    ratio=4.0,
    attack_ms=5.0,
    release_ms=50.0,
    deess_threshold_db=-20.0,
    deess_reduction_db=-6.0,
    limiter_ceiling_db=-1.0
):
    """
    Full DSP pipeline for vocal processing.
    """

    # 1. High-pass filter
    processed = high_pass_filter(audio, cutoff_hz=hp_cutoff)

    # 2. EQ
    processed = apply_eq(
        processed,
        low_gain_db=low_gain_db,
        mid_gain_db=mid_gain_db,
        high_gain_db=high_gain_db
    )

    # 3. Compression
    processed = apply_compression(
        processed,
        threshold_db=threshold_db,
        ratio=ratio,
        attack_ms=attack_ms,
        release_ms=release_ms
    )

    # 4. De-esser
    processed = apply_deesser(
        processed,
        threshold_db=deess_threshold_db,
        reduction_db=deess_reduction_db
    )

    # 5. Limiter
    processed = apply_limiter(processed, ceiling_db=limiter_ceiling_db)

    return processed
