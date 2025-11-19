"""
Release Service for Label-in-a-Box - PHASE 5
Builds standardized release packs with metadata, cover art, and audio.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import numpy as np

try:
    from pydub import AudioSegment
    from pydub.utils import db_to_float, float_to_db
except ImportError:
    AudioSegment = None
    db_to_float = None
    float_to_db = None

from backend.release.cover_generator import CoverArtGenerator
from backend.release.utils import sanitize_filename

logger = logging.getLogger(__name__)


class ReleaseService:
    """
    Service for building standardized release packs.
    Enforces folder structure: /media/{user_id}/{session_id}/release/
    """
    
    def __init__(self):
        self.cover_generator = CoverArtGenerator()
    
    def build_release_pack(
        self,
        session_id: str,
        title: str,
        artist: str,
        mixed_file_path: Path,
        cover_prompt: Optional[str] = None,
        release_date: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Build complete release pack with standardized structure.
        
        Args:
            session_id: Session identifier
            title: Song title
            artist: Artist name
            mixed_file_path: Path to mixed/mastered WAV file
            cover_prompt: Optional prompt for cover generation
            release_date: ISO8601 date string (defaults to today)
            
        Returns:
            Dict with ok, data (urls), error (if failed)
        """
        try:
            logger.info(f"Building release pack for session {session_id}...")
            
            # Validate inputs
            if not title or not title.strip():
                return {"ok": False, "error": "MISSING_FIELD", "field": "title"}
            if not artist or not artist.strip():
                return {"ok": False, "error": "MISSING_FIELD", "field": "artist"}
            if not session_id or not session_id.strip():
                return {"ok": False, "error": "MISSING_FIELD", "field": "session_id"}
            if not mixed_file_path.exists():
                return {"ok": False, "error": "MISSING_FIELD", "field": "mixed_file"}
            
            # Set up release directory structure
            if user_id:
                release_dir = Path("./media") / user_id / session_id / "release"
            else:
                release_dir = Path("./media") / session_id / "release"
            release_dir.mkdir(parents=True, exist_ok=True)
            
            # Sanitize filenames
            safe_title = sanitize_filename(title)
            safe_artist = sanitize_filename(artist)
            
            # 1. Copy/rename audio file
            audio_filename = f"{safe_artist}_{safe_title}.wav"
            audio_path = release_dir / audio_filename
            logger.info(f"Copying audio to {audio_path}")
            if mixed_file_path != audio_path:
                import shutil
                shutil.copy2(mixed_file_path, audio_path)
            logger.info(f"Audio saved to {audio_path}")
            
            # 2. Analyze audio for metadata
            audio_analysis = self._analyze_audio(audio_path)
            
            # 3. Generate cover art
            cover_path = release_dir / "cover.png"
            cover_result = self.cover_generator.generate_cover(
                track_title=title,
                artist_name=artist,
                output_path=cover_path,
                cover_prompt=cover_prompt
            )
            
            if not cover_result.get("ok"):
                return {"ok": False, "error": "COVER_GENERATION_FAILED", "details": cover_result.get("error")}
            
            logger.info(f"Cover saved to {cover_path}")
            
            # 4. Generate metadata JSON
            if not release_date:
                release_date = datetime.now().isoformat()
            
            metadata = {
                "title": title,
                "artist": artist,
                "release_date": release_date,
                "session_id": session_id,
                "duration_ms": audio_analysis["duration_ms"],
                "loudness_dBFS": audio_analysis["loudness_dBFS"],
                "peak_dBFS": audio_analysis["peak_dBFS"],
                "rms": audio_analysis["rms"]
            }
            
            metadata_path = release_dir / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Metadata saved to {metadata_path}")
            
            # 5. Create placeholder social_clip.mp4 (empty file for now)
            social_clip_path = release_dir / "social_clip.mp4"
            if not social_clip_path.exists():
                social_clip_path.touch()  # Create empty placeholder
                logger.info(f"Placeholder social_clip.mp4 created at {social_clip_path}")
            
            # Verify all files exist
            required_files = [cover_path, audio_path, metadata_path]
            for file_path in required_files:
                if not file_path.exists():
                    return {"ok": False, "error": "FILE_CREATION_FAILED", "file": str(file_path)}
            
            # Return response with URLs
            if user_id:
                base_url = f"/media/{user_id}/{session_id}/release"
            else:
                base_url = f"/media/{user_id}/{session_id}/release"
            return {
                "ok": True,
                "data": {
                    "cover_url": f"{base_url}/cover.png",
                    "song_url": f"{base_url}/{audio_filename}",
                    "metadata_url": f"{base_url}/metadata.json",
                    "folder": f"{base_url}/"
                },
                "message": "Release pack successfully created."
            }
            
        except Exception as e:
            logger.error(f"Release pack build failed: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}
    
    def _analyze_audio(self, audio_path: Path) -> Dict:
        """
        Analyze audio file to compute loudness, peak, RMS.
        
        Args:
            audio_path: Path to WAV file
            
        Returns:
            Dict with duration_ms, loudness_dBFS, peak_dBFS, rms
        """
        if AudioSegment is None:
            logger.warning("pydub not available, using default audio analysis values")
            return {
                "duration_ms": 0,
                "loudness_dBFS": -23.0,
                "peak_dBFS": -3.0,
                "rms": 0.5
            }
        
        try:
            audio = AudioSegment.from_file(str(audio_path))
            duration_ms = len(audio)
            
            # Convert to numpy array for analysis
            samples = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
                samples = samples.mean(axis=1)  # Mono mix
            
            # Normalize to float [-1.0, 1.0]
            if audio.sample_width == 1:
                samples = samples.astype(np.float32) / 128.0 - 1.0
            elif audio.sample_width == 2:
                samples = samples.astype(np.float32) / 32768.0
            elif audio.sample_width == 4:
                samples = samples.astype(np.float32) / 2147483648.0
            else:
                samples = samples.astype(np.float32) / (2 ** (audio.sample_width * 8 - 1))
            
            # Compute RMS (Root Mean Square)
            rms = float(np.sqrt(np.mean(samples ** 2)))
            
            # Compute peak (maximum absolute value)
            peak = float(np.abs(samples).max())
            
            # Convert to dBFS
            if rms > 0:
                loudness_dBFS = float(20 * np.log10(rms))
            else:
                loudness_dBFS = -120.0  # Silence
            
            if peak > 0:
                peak_dBFS = float(20 * np.log10(peak))
            else:
                peak_dBFS = -120.0
            
            return {
                "duration_ms": duration_ms,
                "loudness_dBFS": round(loudness_dBFS, 2),
                "peak_dBFS": round(peak_dBFS, 2),
                "rms": round(rms, 4)
            }
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            # Return defaults on error
            return {
                "duration_ms": 0,
                "loudness_dBFS": -23.0,
                "peak_dBFS": -3.0,
                "rms": 0.5
            }

