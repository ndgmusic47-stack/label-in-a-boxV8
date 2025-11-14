"""
Voice/Personality System for Label-in-a-Box v4
7 AI voices with distinct personalities using OpenAI TTS
"""

import os
import logging
from typing import Optional, Dict, List
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

# Voice Personality Definitions
VOICES = {
    "nova": {
        "name": "Nova",
        "role": "A&R / Creative Director",
        "personality": "visionary, calm, guiding",
        "tts_voice": "nova",  # OpenAI TTS voice
        "style": "strategic and inspiring"
    },
    "echo": {
        "name": "Echo",
        "role": "Producer / Engineer",
        "personality": "precise, technical, detail-oriented",
        "tts_voice": "echo",
        "style": "professional and analytical"
    },
    "lyrica": {
        "name": "Lyrica",
        "role": "Songwriter / Coach",
        "personality": "warm, expressive, encouraging",
        "tts_voice": "shimmer",
        "style": "creative and supportive"
    },
    "tone": {
        "name": "Tone",
        "role": "Mix Specialist",
        "personality": "professional, analytical, perfection-focused",
        "tts_voice": "onyx",
        "style": "technical and precise"
    },
    "aria": {
        "name": "Aria",
        "role": "Label Manager",
        "personality": "organized, businesslike, efficient",
        "tts_voice": "alloy",
        "style": "professional and structured"
    },
    "vee": {
        "name": "Vee",
        "role": "Marketing Director",
        "personality": "fast-talking, social-media energy, hype",
        "tts_voice": "fable",
        "style": "energetic and trend-focused"
    },
    "pulse": {
        "name": "Pulse",
        "role": "Analyst",
        "personality": "clear, data-driven, objective",
        "tts_voice": "onyx",
        "style": "factual and insightful"
    }
}

class VoiceAgent:
    """
    Represents an AI voice personality that can speak and interact
    """
    
    def __init__(self, voice_id: str, media_dir: Path):
        if voice_id not in VOICES:
            raise ValueError(f"Unknown voice: {voice_id}")
        
        self.voice_id = voice_id
        self.config = VOICES[voice_id]
        self.media_dir = media_dir
        self.tts_cache_dir = media_dir / "voice_cache"
        self.tts_cache_dir.mkdir(exist_ok=True)
    
    def get_context_prompt(self, message: str, project_context: str = "") -> str:
        """
        Generate a contextual prompt for this voice personality
        """
        prompt = f"You are {self.config['name']}, the {self.config['role']} at Label-in-a-Box. "
        prompt += f"Your personality is {self.config['personality']}. "
        prompt += f"Speak in a {self.config['style']} manner. "
        
        if project_context:
            prompt += f"\n\nProject context:\n{project_context}\n\n"
        
        prompt += f"Respond to this: {message}"
        
        return prompt
    
    async def speak(self, text: str, speed: float = 1.0) -> Dict:
        """
        Generate TTS audio for the given text
        Returns: {file_url, text, duration_ms}
        """
        try:
            # Check if OpenAI API key is available
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY not set - voice system in placeholder mode")
                return {
                    "voice": self.voice_id,
                    "text": text,
                    "file_url": None,
                    "provider": "placeholder",
                    "message": "TTS disabled - OpenAI API key required"
                }
            
            # Import OpenAI here to avoid dependency issues
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except ImportError:
                logger.error("OpenAI package not installed")
                return {
                    "voice": self.voice_id,
                    "text": text,
                    "file_url": None,
                    "provider": "error",
                    "message": "OpenAI package not installed"
                }
            
            # Generate cache key for this text + voice
            cache_key = hashlib.md5(f"{self.voice_id}:{text}:{speed}".encode()).hexdigest()
            cache_file = self.tts_cache_dir / f"{cache_key}.mp3"
            
            # Return cached version if exists
            if cache_file.exists():
                logger.info(f"Using cached TTS for {self.voice_id}")
                return {
                    "voice": self.voice_id,
                    "name": self.config["name"],
                    "text": text,
                    "file_url": f"/media/voice_cache/{cache_key}.mp3",
                    "provider": "openai_cached"
                }
            
            # Generate new TTS
            response = client.audio.speech.create(
                model="tts-1",  # or tts-1-hd for higher quality
                voice=self.config["tts_voice"],
                input=text,
                speed=speed
            )
            
            # Save to cache
            response.stream_to_file(str(cache_file))
            
            logger.info(f"{self.config['name']} spoke: {text[:50]}...")
            
            return {
                "voice": self.voice_id,
                "name": self.config["name"],
                "text": text,
                "file_url": f"/media/voice_cache/{cache_key}.mp3",
                "provider": "openai"
            }
            
        except Exception as e:
            logger.error(f"TTS error for {self.voice_id}: {e}")
            return {
                "voice": self.voice_id,
                "text": text,
                "file_url": None,
                "provider": "error",
                "message": str(e)
            }
    
    async def respond(self, message: str, project_context: str = "") -> Dict:
        """
        Generate a contextual response and speak it
        """
        try:
            if not os.getenv("OPENAI_API_KEY"):
                response_text = f"[{self.config['name']}] {message}"
                return await self.speak(response_text)
            
            # Import OpenAI
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except ImportError:
                response_text = f"[{self.config['name']}] OpenAI not configured"
                return await self.speak(response_text)
            
            # Generate contextual response
            prompt = self.get_context_prompt(message, project_context)
            
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            response_text = completion.choices[0].message.content
            if response_text:
                response_text = response_text.strip()
            else:
                response_text = f"I'm {self.config['name']}, ready to help."
            
            # Speak the response
            speech_result = await self.speak(response_text)
            speech_result["generated_response"] = True
            
            return speech_result
            
        except Exception as e:
            logger.error(f"Response generation error for {self.voice_id}: {e}")
            fallback_text = f"I'm {self.config['name']}, your {self.config['role']}. Let's keep working."
            return await self.speak(fallback_text)

def get_voice_agent(voice_id: str, media_dir: Path) -> VoiceAgent:
    """Factory function to get a voice agent"""
    return VoiceAgent(voice_id, media_dir)

def get_all_voices() -> Dict:
    """Get information about all available voices"""
    return VOICES

def get_voice_for_context(context: str) -> str:
    """
    Suggest which voice should speak based on context
    """
    context_lower = context.lower()
    
    if any(word in context_lower for word in ["beat", "produce", "sound", "audio"]):
        return "echo"
    elif any(word in context_lower for word in ["lyric", "write", "bar", "verse"]):
        return "lyrica"
    elif any(word in context_lower for word in ["mix", "master", "eq", "compress"]):
        return "tone"
    elif any(word in context_lower for word in ["release", "distribute", "schedule"]):
        return "aria"
    elif any(word in context_lower for word in ["market", "social", "post", "content"]):
        return "vee"
    elif any(word in context_lower for word in ["analytics", "streams", "data", "metrics"]):
        return "pulse"
    else:
        return "nova"  # Default A&R voice
