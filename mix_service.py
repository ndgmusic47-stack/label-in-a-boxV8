from pydub import AudioSegment
import os
from pathlib import Path

def apply_basic_mix(vocal_path: str, beat_path: str, output_path: str):
    # Load audio
    vocal = AudioSegment.from_file(vocal_path)
    beat = AudioSegment.from_file(beat_path)

    # Simple DSP chain
    # 1. Align lengths
    min_len = min(len(vocal), len(beat))
    vocal = vocal[:min_len]
    beat = beat[:min_len]

    # 2. Normalize both
    vocal = vocal.normalize()
    beat = beat.normalize()

    # 3. High-pass filter vocal
    vocal = vocal.high_pass_filter(120)

    # 4. Light compression on vocal
    vocal = vocal.compress_dynamic_range()

    # 5. Combine
    mix = beat.overlay(vocal, gain_during_overlay=-2)

    # 6. Export
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    mix.export(output_path, format="wav")



