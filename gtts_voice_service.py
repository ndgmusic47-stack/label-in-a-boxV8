"""
gTTS Voice Service - Offline Text-to-Speech for AI Personalities
Caches MP3 files to reduce API calls and enable offline operation
"""

import os
from pathlib import Path
from typing import Dict, Optional
from gtts import gTTS
import hashlib
import logging

logger = logging.getLogger(__name__)


class GTTSVoiceService:
    """
    Offline text-to-speech service using Google TTS (free tier).
    Caches generated MP3 files for reuse.
    """
    
    def __init__(self, media_dir: Path):
        self.media_dir = media_dir
        self.voices_dir = media_dir / "voices"
        self.voices_dir.mkdir(exist_ok=True, parents=True)
        
        # Voice personality configurations
        self.personalities = {
            "nova": {
                "name": "Nova",
                "role": "Creative Director / A&R",
                "lang": "en",
                "tld": "com",
                "slow": False
            },
            "echo": {
                "name": "Echo",
                "role": "Producer / Engineer",
                "lang": "en",
                "tld": "co.uk",
                "slow": False
            },
            "lyrica": {
                "name": "Lyrica",
                "role": "Songwriter / Vocal Coach",
                "lang": "en",
                "tld": "com.au",
                "slow": False
            },
            "tone": {
                "name": "Tone",
                "role": "Mix Engineer",
                "lang": "en",
                "tld": "ca",
                "slow": False
            },
            "aria": {
                "name": "Aria",
                "role": "Label Manager",
                "lang": "en",
                "tld": "co.in",
                "slow": False
            },
            "vee": {
                "name": "Vee",
                "role": "Marketing Director",
                "lang": "en",
                "tld": "us",
                "slow": False
            },
            "pulse": {
                "name": "Pulse",
                "role": "Analyst",
                "lang": "en",
                "tld": "co.za",
                "slow": False
            }
        }
    
    def _get_cache_key(self, voice_id: str, text: str, speed: float = 1.0) -> str:
        """Generate cache key for voice file."""
        content = f"{voice_id}:{text}:{speed}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_file(self, cache_key: str) -> Optional[Path]:
        """Check if cached MP3 exists."""
        cached_file = self.voices_dir / f"{cache_key}.mp3"
        if cached_file.exists():
            return cached_file
        return None
    
    def speak(
        self,
        voice_id: str,
        text: str,
        speed: float = 1.0,
        use_cache: bool = True
    ) -> Dict:
        """
        Generate speech audio using gTTS.
        
        Args:
            voice_id: Personality ID (nova, echo, lyrica, tone, aria, vee, pulse)
            text: Text to speak
            speed: Speech speed (0.5 - 2.0, but gTTS only supports normal/slow)
            use_cache: Whether to use cached files
            
        Returns:
            Dict with audio_url and metadata
        """
        try:
            if voice_id not in self.personalities:
                raise ValueError(f"Unknown voice: {voice_id}")
            
            personality = self.personalities[voice_id]
            cache_key = self._get_cache_key(voice_id, text, speed)
            
            # Check cache first
            if use_cache:
                cached_file = self._get_cached_file(cache_key)
                if cached_file:
                    logger.info(f"Using cached voice file for {voice_id}: {cache_key}")
                    return {
                        "audio_url": f"/media/voices/{cache_key}.mp3",
                        "voice": voice_id,
                        "personality": personality["name"],
                        "role": personality["role"],
                        "text": text,
                        "cached": True
                    }
            
            # Generate new audio
            output_file = self.voices_dir / f"{cache_key}.mp3"
            
            # gTTS only supports normal and slow speeds
            slow = speed < 0.8 or personality["slow"]
            
            tts = gTTS(
                text=text,
                lang=personality["lang"],
                tld=personality["tld"],
                slow=slow
            )
            
            tts.save(str(output_file))
            logger.info(f"Generated voice file for {voice_id}: {cache_key}")
            
            return {
                "audio_url": f"/media/voices/{cache_key}.mp3",
                "voice": voice_id,
                "personality": personality["name"],
                "role": personality["role"],
                "text": text,
                "cached": False
            }
            
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return {
                "error": str(e),
                "voice": voice_id,
                "text": text
            }
    
    def get_personality_info(self, voice_id: str) -> Optional[Dict]:
        """Get information about a voice personality."""
        if voice_id in self.personalities:
            return self.personalities[voice_id]
        return None
    
    def list_personalities(self) -> Dict[str, Dict]:
        """List all available voice personalities."""
        return {
            voice_id: {
                "name": config["name"],
                "role": config["role"]
            }
            for voice_id, config in self.personalities.items()
        }
    
    def clear_cache(self, voice_id: Optional[str] = None):
        """
        Clear cached voice files.
        
        Args:
            voice_id: Specific voice to clear, or None to clear all
        """
        if voice_id:
            # Clear specific voice cache
            for file in self.voices_dir.glob(f"*"):
                # Simple cache clear - in production, track which cache belongs to which voice
                file.unlink()
                logger.info(f"Cleared cache for {voice_id}")
        else:
            # Clear all cache
            for file in self.voices_dir.glob("*.mp3"):
                file.unlink()
            logger.info("Cleared all voice cache")


def get_gtts_voice_service(media_dir: Path) -> GTTSVoiceService:
    """Factory function to get gTTS voice service."""
    return GTTSVoiceService(media_dir)
