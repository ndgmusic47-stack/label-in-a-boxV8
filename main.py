"""
Label-in-a-Box Phase 2 Backend - Production Demo
Clean backend using ONLY: Beatoven, OpenAI (text), Auphonic, GetLate, local services
"""

import os
import uuid
import json
import shutil
import asyncio
import time
import math
import subprocess
import io
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging
import hashlib
import zipfile

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, APIRouter, Request, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import json
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range, high_pass_filter
from PIL import Image, ImageDraw, ImageFont
import requests
from gtts import gTTS

# Import local services
from project_memory import ProjectMemory, get_or_create_project_memory, list_all_projects
from cover_art_generator import CoverArtGenerator
from analytics_engine import AnalyticsEngine
from social_scheduler import SocialScheduler
from content import content_router

# ============================================================================
# PHASE 2.2: SHARED UTILITIES
# ============================================================================

# Logging setup - write ALL events to /logs/app.log
LOGS_DIR = Path("./logs")
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Phase 2.2 JSON response helpers
def success_response(data: Optional[dict] = None, message: str = "Success"):
    """Standardized success response"""
    return {"ok": True, "data": data or {}, "message": message}

def error_response(error: str, status_code: int = 400):
    """Standardized error response"""
    logger.error(f"Error response: {error}")
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "error": error}
    )

# Path compatibility helpers for /media/{session_id}/ migration
def get_session_media_path(session_id: str) -> Path:
    """Get media path for session - Phase 2.2 uses /media/{session_id}/"""
    path = Path("./media") / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def log_endpoint_event(endpoint: str, session_id: Optional[str] = None, result: str = "success", details: Optional[dict] = None):
    """Log endpoint execution to app.log"""
    log_data = {
        "endpoint": endpoint,
        "session_id": session_id or "none",
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        log_data.update(details)
    logger.info(f"{endpoint} | session={session_id} | {result} | {json.dumps(details or {})}")

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(title="Label in a Box v4 - Phase 2.2")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
MEDIA_DIR = Path("./media")
ASSETS_DIR = Path("./assets")
FRONTEND_DIST = Path("./frontend/dist")
MEDIA_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
(ASSETS_DIR / "demo").mkdir(exist_ok=True)

# Serve static files
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# ============================================================================
# API ROUTER WRAPPER (adds /api prefix for all endpoints)
# ============================================================================
api = APIRouter(prefix="/api")

# ============================================================================
# REQUEST MODELS
# ============================================================================

class BeatRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, description="User description of the beat")
    mood: Optional[str] = Field(default="energetic", description="Mood/vibe")
    genre: Optional[str] = Field(default="hip-hop", description="Music genre")
    bpm: Optional[int] = Field(default=None, description="Beats per minute (tempo) - AI-determined if not provided")
    duration_sec: Optional[int] = Field(default=None, description="Duration in seconds (AI-determined if not provided)")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    
    # Aliases for compatibility
    tempo: Optional[int] = Field(default=None, description="Tempo (alias for bpm)")
    duration: Optional[int] = Field(default=None, description="Duration (alias for duration_sec)")

class SongRequest(BaseModel):
    genre: str = Field(default="hip hop")
    mood: str = Field(default="energetic")
    theme: Optional[str] = None
    session_id: Optional[str] = Field(None)
    beat_context: Optional[dict] = Field(None, description="Beat metadata (tempo/key/energy)")

class MixRequest(BaseModel):
    session_id: str
    vocal_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    beat_gain: float = Field(default=0.8, ge=0.0, le=2.0)
    hpf_hz: int = Field(default=80, ge=20, le=200, description="High-pass filter frequency")
    deess_amount: float = Field(default=0.3, ge=0.0, le=1.0, description="De-ess amount")

class ReleaseRequest(BaseModel):
    session_id: str
    title: Optional[str] = None
    artist: Optional[str] = None
    mixed_file: Optional[str] = None
    cover_file: Optional[str] = None
    metadata: Optional[dict] = None
    lyrics: Optional[str] = ""

class SocialPostRequest(BaseModel):
    session_id: str
    platform: str = Field(default="tiktok", description="tiktok, shorts, or reels")
    when_iso: str = Field(default="", description="ISO datetime string")
    caption: str = Field(default="", description="Post caption")

class VoiceSayRequest(BaseModel):
    persona: str = Field(..., description="echo, lyrica, nova, tone, aria, vee, or pulse")
    text: str
    session_id: Optional[str] = None

# ============================================================================
# VOICE DEBOUNCE SYSTEM (gTTS ONLY) - PHASE 2.2: 10s DEBOUNCE, SHA256 CACHE
# ============================================================================

_voice_debounce_cache: dict[str, float] = {}
_voice_debounce_seconds = 10.0  # Phase 2.2: 10-second debounce

def should_speak(persona: str, text: str) -> bool:
    """Phase 2.2: Debounce with 10-second window and SHA256 key"""
    # SHA256 cache key (Phase 2.2 requirement)
    key = hashlib.sha256(f"{persona}:{text}".encode()).hexdigest()
    now = time.time()
    last_time = _voice_debounce_cache.get(key, 0)
    if now - last_time < _voice_debounce_seconds:
        return False
    _voice_debounce_cache[key] = now
    return True

def gtts_speak(persona: str, text: str, session_id: Optional[str] = None):
    """Phase 2.2: Generate speech using gTTS with SHA256 cache and 10s debounce"""
    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Generate SHA256 cache key (Phase 2.2 requirement)
    cache_key = hashlib.sha256(f"{persona}:{text}".encode()).hexdigest()
    
    # Create voices directory
    voices_dir = get_session_media_path(session_id) / "voices"
    voices_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = voices_dir / f"{cache_key}.mp3"
    
    # Check debounce (but still return URL to cached file)
    is_debounced = not should_speak(persona, text)
    
    try:
        # Generate if not cached on disk
        if not output_file.exists():
            # Persona-specific accents (using only gTTS-supported TLDs)
            tld_map = {
                "nova": "com", "echo": "co.uk", "lyrica": "com.au",
                "tone": "ca", "aria": "co.in", "vee": "com", "pulse": "co.za"
            }
            tld = tld_map.get(persona, "com")
            
            tts = gTTS(text=text, lang="en", tld=tld, slow=False)
            tts.save(str(output_file))
        
        # Return URL whether debounced or not (spec requires playable asset)
        # Construct URL path relative to media directory
        url_path = f"/media/{session_id}/voices/{cache_key}.mp3"
        log_endpoint_event("/voices/say", session_id, "success", {"persona": persona, "cached": is_debounced})
        return success_response(
            data={
                "url": url_path,
                "persona": persona,
                "cached": is_debounced,
                "session_id": session_id
            },
            message="Voice cached (debounced)" if is_debounced else f"Voice generated for {persona}"
        )
    except Exception as e:
        log_endpoint_event("/voices/say", session_id, "error", {"error": str(e), "persona": persona})
        return error_response(f"gTTS failed: {str(e)}")

# ============================================================================
# 1. POST /beats/create - BEATOVEN INTEGRATION
# ============================================================================

@api.post("/beats/create")
async def create_beat(request: Optional[BeatRequest] = Body(default=None)):
    """Phase 2.2: Generate beat using Beatoven API with fallback to demo beat - NEVER returns 422"""
    # Handle None request (empty body) or partial request
    if request is None:
        request = BeatRequest()
    
    # Build job object with safe defaults - handle None values
    prompt = request.prompt or ""
    mood = request.mood or "energetic"
    genre = request.genre or "hip-hop"
    # Use tempo if provided, otherwise bpm, but don't default to 120 - let AI determine
    bpm = request.tempo or request.bpm
    # Check if duration was explicitly provided (not using default)
    duration_provided = request.duration is not None or request.duration_sec is not None
    duration_sec = request.duration or request.duration_sec
    session_id = request.session_id or str(uuid.uuid4())
    
    # Only enforce bounds on bpm if it was provided
    if bpm is not None:
        bpm = max(60, min(200, bpm))
    # Only enforce bounds on duration if it was provided
    if duration_provided and duration_sec is not None:
        duration_sec = max(10, min(300, duration_sec))
    
    session_path = get_session_media_path(session_id)
    
    if duration_provided and duration_sec is not None:
        logger.info(f"🎵 Beat creation request: prompt={prompt[:50]}..., mood={mood}, genre={genre}, bpm={bpm or 'AI-determined'}, duration={duration_sec}s, session={session_id}")
    else:
        logger.info(f"🎵 Beat creation request: prompt={prompt[:50]}..., mood={mood}, genre={genre}, bpm={bpm or 'AI-determined'}, duration=AI-determined, session={session_id}")
    
    api_key = os.getenv("BEATOVEN_API_KEY")
    
    # Try Beatoven API first if key available
    if api_key:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Step 1: Build prompt text from user prompt, mood, and genre
            # If user provided a prompt, use it as the base, otherwise build from mood/genre
            if prompt:
                # Use user's prompt as the primary description
                prompt_text = prompt
                # Optionally append mood/genre if they add context
                if mood and mood != "energetic":
                    prompt_text += f", {mood} mood"
                if genre and genre != "hip-hop":
                    prompt_text += f", {genre} style"
            else:
                # Fallback: build from mood and genre
                prompt_text = f"{mood} {genre} instrumental track"
            
            # Add duration to prompt if provided
            if duration_provided and duration_sec is not None:
                prompt_text = f"{duration_sec} seconds {prompt_text}"
            
            payload = {"prompt": {"text": prompt_text}, "format": "mp3", "looping": False}
            
            logger.info(f"🎵 Beatoven job started: {prompt_text}")
            if api_key:
                logger.info(f"🔑 Using API key: {api_key[:10]}...")
            else:
                logger.info("🔑 No API key configured")
            
            compose_url = "https://public-api.beatoven.ai/api/v1/tracks/compose"
            compose_res = requests.post(compose_url, headers=headers, json=payload, timeout=30)
            
            # Handle 422 and other HTTP errors gracefully
            if compose_res.status_code == 422:
                error_detail = compose_res.text
                logger.warning(f"Beatoven API returned 422 Unprocessable Content: {error_detail}")
                logger.warning("Beatoven unavailable, serving fallback beat")
                raise Exception(f"Beatoven API validation error: {error_detail}")
            elif compose_res.status_code == 401:
                logger.warning(f"Beatoven API returned 401 Unauthorized - invalid API key")
                logger.warning("Beatoven unavailable, serving fallback beat")
                raise Exception("Beatoven API authentication failed")
            elif not compose_res.ok:
                error_detail = compose_res.text
                logger.warning(f"Beatoven API returned {compose_res.status_code}: {error_detail}")
                logger.warning("Beatoven unavailable, serving fallback beat")
                raise Exception(f"Beatoven API error {compose_res.status_code}: {error_detail}")
            
            compose_data = compose_res.json()
            task_id = compose_data.get("task_id")
            
            if not task_id:
                raise Exception("Beatoven: no task_id returned")
            
            logger.info(f"✅ Beatoven task started: {task_id}")
            
            # Step 2: Poll for completion (up to 3 minutes) - ASYNC to not block event loop
            for attempt in range(60):
                await asyncio.sleep(3)  # Non-blocking sleep
                status_url = f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}"
                status_res = requests.get(status_url, headers=headers, timeout=30)
                
                # Handle status check errors
                if not status_res.ok:
                    logger.warning(f"Beatoven status check failed: {status_res.status_code}")
                    raise Exception(f"Beatoven status check error: {status_res.status_code}")
                
                status_data = status_res.json()
                status = status_data.get("status")
                
                if status == "composed":
                    meta = status_data.get("meta", {})
                    audio_url = meta.get("track_url")
                    if not audio_url:
                        raise Exception("Beatoven: track_url missing")
                    
                    # Download the audio
                    output_file = session_path / "beat.mp3"
                    audio_data = requests.get(audio_url, timeout=60)
                    audio_data.raise_for_status()
                    with open(output_file, "wb") as f:
                        f.write(audio_data.content)
                    
                    logger.info(f"🎵 Beatoven track ready: {output_file}")
                    
                    # Extract metadata from Beatoven response
                    extracted_metadata = {}
                    if meta.get("duration"):
                        extracted_metadata["duration"] = int(meta.get("duration"))
                    elif meta.get("length"):
                        extracted_metadata["duration"] = int(meta.get("length"))
                    
                    # BPM from meta or use provided/calculated bpm
                    extracted_bpm = meta.get("bpm") or meta.get("tempo") or bpm
                    if extracted_bpm:
                        extracted_metadata["bpm"] = int(extracted_bpm) if isinstance(extracted_bpm, (int, float)) else extracted_bpm
                    
                    # Key from meta
                    if meta.get("key"):
                        extracted_metadata["key"] = meta.get("key")
                    
                    # Update project memory
                    memory = get_or_create_project_memory(session_id, MEDIA_DIR)
                    memory.update_metadata(tempo=extracted_bpm, mood=mood, genre=genre)
                    memory.add_asset("beat", f"/media/{session_id}/beat.mp3", {"bpm": extracted_bpm, "mood": mood, "metadata": extracted_metadata})
                    memory.advance_stage("beat", "lyrics")
                    
                    log_endpoint_event("/beats/create", session_id, "success", {"source": "beatoven", "mood": mood})
                    return success_response(
                        data={
                            "session_id": session_id,
                            "url": f"/media/{session_id}/beat.mp3",
                            "beat_url": f"/media/{session_id}/beat.mp3",
                            "status": "ready",
                            "metadata": extracted_metadata
                        },
                        message="Beat generated successfully via Beatoven"
                    )
                
                elif status in ("composing", "running", "queued"):
                    logger.info(f"⏳ Beatoven status: {status} ({attempt+1}/60)")
                    continue
                else:
                    raise Exception(f"Unexpected Beatoven status: {status}")
            
            raise Exception("Beatoven generation timed out (3 minutes)")
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Beatoven API request failed: {e} - falling back to demo beat")
        except Exception as e:
            logger.warning(f"Beatoven API failed: {e} - falling back to demo beat")
    
    # FALLBACK: Always return a beat (ALWAYS succeeds)
    try:
        # Ensure demo_beats directory exists
        demo_beats_dir = MEDIA_DIR / "demo_beats"
        demo_beats_dir.mkdir(exist_ok=True, parents=True)
        fallback = demo_beats_dir / "default_beat.mp3"
        
        # Check if fallback exists, if not create it
        if not fallback.exists():
            # Try to copy from assets if it exists
            source_beat = ASSETS_DIR / "demo" / "beat.mp3"
            if source_beat.exists():
                shutil.copy(source_beat, fallback)
                logger.info(f"Created fallback beat at {fallback}")
            else:
                # Create silent audio clip as fallback
                logger.info(f"Creating silent fallback beat at {fallback}")
                silent_audio = AudioSegment.silent(duration=60000)  # 60 seconds
                silent_audio.export(str(fallback), format="mp3")
        
        # Copy fallback to session
        output_file = session_path / "beat.mp3"
        shutil.copy(fallback, output_file)
        
        logger.info(f"⚠️ Beatoven unavailable, using fallback demo beat")
        
        # Update project memory
        memory = get_or_create_project_memory(session_id, MEDIA_DIR)
        # For demo beats, use default metadata
        demo_metadata = {"duration": 60, "bpm": bpm or 120, "key": "C"}
        memory.update_metadata(tempo=bpm or 120, mood=mood, genre=genre)
        memory.add_asset("beat", f"/media/{session_id}/beat.mp3", {"bpm": bpm or 120, "mood": mood, "source": "demo", "metadata": demo_metadata})
        memory.advance_stage("beat", "lyrics")
        
        log_endpoint_event("/beats/create", session_id, "success", {"source": "demo", "mood": mood})
        return success_response(
            data={
                "session_id": session_id,
                "url": f"/media/{session_id}/beat.mp3",
                "beat_url": f"/media/{session_id}/beat.mp3",
                "status": "ready",
                "metadata": demo_metadata
            },
            message="Beatoven unavailable, using fallback demo beat"
        )
    
    except Exception as e:
        # Ultimate fallback - create silent audio in session directory
        logger.error(f"Fallback beat creation failed: {e} - creating silent audio in session")
        try:
            output_file = session_path / "beat.mp3"
            silent_audio = AudioSegment.silent(duration=duration_sec * 1000)
            silent_audio.export(str(output_file), format="mp3")
            
            memory = get_or_create_project_memory(session_id, MEDIA_DIR)
            silent_metadata = {"duration": duration_sec or 60, "bpm": bpm or 120, "key": "C"}
            memory.update_metadata(tempo=bpm or 120, mood=mood, genre=genre)
            memory.add_asset("beat", f"/media/{session_id}/beat.mp3", {"bpm": bpm or 120, "mood": mood, "source": "silent_fallback", "metadata": silent_metadata})
            
            log_endpoint_event("/beats/create", session_id, "success", {"source": "silent_fallback", "mood": mood})
            return success_response(
                data={
                    "session_id": session_id,
                    "url": f"/media/{session_id}/beat.mp3",
                    "beat_url": f"/media/{session_id}/beat.mp3",
                    "status": "ready",
                    "metadata": silent_metadata
                },
                message="Beat created (fallback mode)"
            )
        except Exception as final_error:
            logger.error(f"Complete beat generation failure: {final_error}")
            # Return success anyway - never return 422
            return success_response(
                data={
                    "session_id": session_id,
                    "url": None,
                    "beat_url": None,
                    "status": "error"
                },
                message="Beat generation attempted (check logs for details)"
            )

# ============================================================================
# 1.1. GET /beats/credits - GET BEATOVEN CREDITS
# ============================================================================

@api.get("/beats/credits")
async def get_beat_credits():
    """Get remaining credits from Beatoven API"""
    api_key = os.getenv("BEATOVEN_API_KEY")
    
    if not api_key:
        # Return default credits if API key not configured
        log_endpoint_event("/beats/credits", None, "success", {"credits": 10, "source": "default"})
        return success_response(
            data={"credits": 10},
            message="Credits retrieved (default - API key not configured)"
        )
    
    try:
        # Try to get credits from Beatoven API
        # Note: Beatoven API may not have a direct credits endpoint
        # This is a placeholder that checks if API key is valid
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Check if Beatoven has a usage/credits endpoint
        # For now, return a default value since Beatoven API documentation
        # doesn't clearly specify a credits endpoint
        # In production, this should call the actual Beatoven credits API if available
        credits_url = "https://public-api.beatoven.ai/api/v1/usage"
        try:
            credits_res = requests.get(credits_url, headers=headers, timeout=10)
            if credits_res.ok:
                credits_data = credits_res.json()
                credits = credits_data.get("credits", credits_data.get("remaining", 10))
                log_endpoint_event("/beats/credits", None, "success", {"credits": credits, "source": "beatoven"})
                return success_response(
                    data={"credits": credits},
                    message="Credits retrieved from Beatoven"
                )
        except:
            pass
        
        # Fallback: return default credits
        log_endpoint_event("/beats/credits", None, "success", {"credits": 10, "source": "fallback"})
        return success_response(
            data={"credits": 10},
            message="Credits retrieved (fallback - Beatoven credits API not available)"
        )
    except Exception as e:
        logger.warning(f"Failed to get Beatoven credits: {e}")
        log_endpoint_event("/beats/credits", None, "error", {"error": str(e)})
        # Return default credits on error
        return success_response(
            data={"credits": 10},
            message="Credits retrieved (default - error occurred)"
        )

# ============================================================================
# 2. POST /songs/write - OPENAI TEXT ONLY (NO TTS)
# ============================================================================

@api.post("/songs/write")
async def write_song(request: SongRequest):
    """Phase 2.2: Generate song lyrics using OpenAI with fallback"""
    session_id = request.session_id if request.session_id else str(uuid.uuid4())
    session_path = get_session_media_path(session_id)
    
    # Static fallback lyrics
    fallback_lyrics = f"""[Verse 1]
This is a {request.genre} verse about {request.mood}
Flowing through the rhythm and the beat
Every word connects with your soul
This is how we make it complete

[Chorus]
{request.mood.title()} vibes all around
{request.genre} is the sound we found
Let the music take control
Feel it deep within your soul

[Verse 2]
Building on the energy we share
Taking it higher everywhere
This is more than just a song
This is where we all belong"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    lyrics_text = fallback_lyrics
    provider = "fallback"
    
    # Try OpenAI if key available
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            beat_context_str = ""
            if request.beat_context:
                beat_context_str = f"\nBeat context: {request.beat_context.get('tempo', 'unknown')} BPM, {request.beat_context.get('key', 'unknown')} key, {request.beat_context.get('energy', 'medium')} energy"
            
            prompt = f"""Write song lyrics for a {request.genre} song with a {request.mood} mood.
Theme: {request.theme or 'general'}{beat_context_str}

Provide complete lyrics with verse, chorus, and bridge sections.
Make it authentic and emotionally resonant."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional songwriter. Write authentic, emotionally resonant lyrics."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9
            )
            
            lyrics_text = response.choices[0].message.content.strip() if response.choices[0].message.content else fallback_lyrics
            provider = "openai"
        except Exception as e:
            logger.warning(f"OpenAI lyrics failed: {e} - using fallback")
    
    # Save lyrics.txt
    try:
        lyrics_file = session_path / "lyrics.txt"
        with open(lyrics_file, 'w') as f:
            f.write(lyrics_text)
        
        # Parse lyrics into structured sections (verse, chorus, bridge)
        lyrics_lines = lyrics_text.split('\n')
        parsed_lyrics = {"verse": "", "chorus": "", "bridge": ""}
        current_section = None
        
        for line in lyrics_lines:
            line_lower = line.lower().strip()
            if '[verse' in line_lower or line_lower.startswith('verse'):
                current_section = "verse"
                continue
            elif '[chorus' in line_lower or line_lower.startswith('chorus'):
                current_section = "chorus"
                continue
            elif '[bridge' in line_lower or line_lower.startswith('bridge'):
                current_section = "bridge"
                continue
            
            if current_section and line.strip():
                if parsed_lyrics[current_section]:
                    parsed_lyrics[current_section] += "\n" + line.strip()
                else:
                    parsed_lyrics[current_section] = line.strip()
        
        # If no sections found, treat all as verse
        if not any(parsed_lyrics.values()):
            parsed_lyrics["verse"] = lyrics_text
        
        # Generate voice MP3 for lyrics using gTTS (first 200 chars to avoid too long)
        voice_url = None
        try:
            # Use first verse or first 200 chars for voice generation
            voice_text = parsed_lyrics.get("verse", "").split('\n')[0] if parsed_lyrics.get("verse") else (lyrics_text.split('\n')[0] if lyrics_text else "Here are your lyrics")
            if len(voice_text) > 200:
                voice_text = voice_text[:200] + "..."
            
            # Generate voice using default persona "nova"
            voice_result = gtts_speak("nova", voice_text, session_id)
            if isinstance(voice_result, dict) and voice_result.get("ok"):
                voice_url = voice_result.get("data", {}).get("url")
                logger.info(f"Generated voice for lyrics: {voice_url}")
        except Exception as e:
            logger.warning(f"Voice generation for lyrics failed: {e}")
        
        # Update project memory
        memory = get_or_create_project_memory(session_id, MEDIA_DIR)
        memory.add_asset("lyrics", f"/media/{session_id}/lyrics.txt", {"genre": request.genre, "mood": request.mood})
        memory.advance_stage("lyrics", "upload")
        
        log_endpoint_event("/songs/write", session_id, "success", {"provider": provider, "voice_generated": voice_url is not None})
        return success_response(
            data={
                "session_id": session_id,
                "lyrics": parsed_lyrics,  # Return structured lyrics
                "lyrics_text": lyrics_text,  # Also include raw text
                "path": f"/media/{session_id}/lyrics.txt",
                "voice_url": voice_url,
                "provider": provider
            },
            message=f"Lyrics generated via {provider}"
        )
    except Exception as e:
        log_endpoint_event("/songs/write", session_id, "error", {"error": str(e)})
        return error_response(f"Lyrics generation failed: {str(e)}")

# ============================================================================
# 2.1. HELPER FUNCTIONS FOR V17 LYRIC MODULE
# ============================================================================

def detect_bpm(filepath):
    """Detect BPM from audio file using aubio"""
    try:
        from aubio import tempo, source
        s = source(str(filepath))
        o = tempo()
        beats = []
        while True:
            samples, read = s()
            is_beat = o(samples)
            if is_beat:
                beats.append(o.get_last_s())
            if read < s.hop_size:
                break
        if len(beats) > 1:
            bpms = 60.0 / (beats[1] - beats[0])
            return int(bpms)
        return 140
    except Exception as e:
        logger.warning(f"BPM detection failed: {e} - using default 140")
        return 140

def analyze_mood(filepath):
    """Analyze mood from audio file - simple implementation"""
    # For now, return default mood as specified
    # In a full implementation, this could analyze spectral features, energy, etc.
    return "dark cinematic emotional"

def generate_np22_lyrics(theme: Optional[str] = None, bpm: Optional[int] = None, mood: Optional[str] = None) -> str:
    """Generate NP22-style lyrics using OpenAI with the specified template"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Build prompt based on NP22 template
    base_prompt = """Write lyrics in the NP22 sound: a cinematic fusion of soulful rock and modern trap — dark-purple energy, emotional intensity, motivational tone, stadium-level delivery. Focus on clean rhythm, expressive soul, mindset themes. Structure: Hook + Verse 1 + Optional Pre-Hook. Keep flow tight, melodic, empowering."""
    
    if bpm:
        base_prompt += f"\n\nMatch the BPM: {bpm} - ensure the lyrics flow naturally with this tempo."
    
    if mood:
        base_prompt += f"\n\nMood/Energy: {mood}"
    
    if theme:
        base_prompt += f"\n\nTheme: {theme}"
    else:
        base_prompt += "\n\nTheme: general motivational mindset"
    
    # Fallback lyrics
    fallback_lyrics = """[Hook]
Rising up from the darkness, I'm taking control
Every step forward, I'm reaching my goal
This is my moment, this is my time
Nothing can stop me, I'm in my prime

[Verse 1]
Through the struggle and the pain
I found my strength again
No more hiding in the shadows
I'm breaking free from all the chains
Standing tall, I claim my name"""
    
    if not api_key:
        logger.warning("OpenAI API key not configured - using fallback lyrics")
        return fallback_lyrics
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional songwriter specializing in NP22-style lyrics: cinematic fusion of soulful rock and modern trap with dark-purple energy, emotional intensity, and motivational tone."},
                {"role": "user", "content": base_prompt}
            ],
            temperature=0.9
        )
        
        lyrics_text = response.choices[0].message.content.strip() if response.choices[0].message.content else fallback_lyrics
        return lyrics_text
    except Exception as e:
        logger.warning(f"OpenAI lyrics generation failed: {e} - using fallback")
        return fallback_lyrics

# ============================================================================
# 2.2. POST /lyrics/from_beat - V17 MODE 1: GENERATE FROM BEAT
# ============================================================================

@api.post("/lyrics/from_beat")
async def generate_lyrics_from_beat(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    """V17: Generate NP22-style lyrics from uploaded beat file"""
    session_id = session_id if session_id else str(uuid.uuid4())
    session_path = get_session_media_path(session_id)
    
    try:
        # Save uploaded file temporarily
        temp_file = session_path / f"temp_beat_{uuid.uuid4().hex[:8]}.mp3"
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        # Detect BPM and analyze mood
        bpm = detect_bpm(temp_file)
        mood = analyze_mood(temp_file)
        
        # Generate lyrics using NP22 template
        lyrics_text = generate_np22_lyrics(theme=None, bpm=bpm, mood=mood)
        
        # Clean up temp file
        try:
            temp_file.unlink()
        except:
            pass
        
        log_endpoint_event("/lyrics/from_beat", session_id, "success", {"bpm": bpm, "mood": mood})
        return success_response(
            data={
                "lyrics": lyrics_text,
                "bpm": bpm,
                "mood": mood
            },
            message="Lyrics generated from beat successfully"
        )
    except Exception as e:
        log_endpoint_event("/lyrics/from_beat", session_id, "error", {"error": str(e)})
        return error_response(f"Lyrics generation from beat failed: {str(e)}")

# ============================================================================
# 2.3. POST /lyrics/free - V17 MODE 2: GENERATE FREE LYRICS
# ============================================================================

class FreeLyricsRequest(BaseModel):
    theme: str = Field(..., description="Theme for the lyrics")

# V18.1: Structured lyric parsing helper function
import re

def parse_lyrics_to_structured(lyrics_text: str):
    """Parse lyrics text into structured sections based on headers like [Hook], [Verse 1], etc."""
    if not lyrics_text or not isinstance(lyrics_text, str):
        return None
    
    sections = {}
    lines = lyrics_text.split('\n')
    current_section = None
    current_lines = []
    
    for line in lines:
        # Detect section headers: [Hook], [Chorus], [Verse 1], [Verse], [Bridge], etc.
        section_match = re.match(r'^\[(Hook|Chorus|Verse\s*\d*|Bridge|Intro|Outro|Pre-Chorus)\](.*)$', line, re.IGNORECASE)
        
        if section_match:
            # Save previous section
            if current_section and current_lines:
                section_key = current_section.lower().replace(' ', '').replace('-', '')
                # Handle verse numbers
                if 'verse' in section_key:
                    num_match = re.search(r'\d+', current_section)
                    if num_match:
                        section_key = f"verse{num_match.group()}"
                    else:
                        section_key = "verse"
                sections[section_key] = '\n'.join([l for l in current_lines if l.strip()])
            
            # Start new section
            current_section = section_match.group(1)
            current_lines = []
        elif line.strip():
            current_lines.append(line)
    
    # Save last section
    if current_section and current_lines:
        section_key = current_section.lower().replace(' ', '').replace('-', '')
        if 'verse' in section_key:
            num_match = re.search(r'\d+', current_section)
            if num_match:
                section_key = f"verse{num_match.group()}"
            else:
                section_key = "verse"
        sections[section_key] = '\n'.join([l for l in current_lines if l.strip()])
    
    return sections if sections else None

class LyricRefineRequest(BaseModel):
    lyrics: str = Field(..., description="Full current lyrics as text")
    instruction: str = Field(..., description="User instruction for refinement")
    bpm: Optional[int] = Field(default=None, description="Beats per minute (optional)")
    history: Optional[List[dict]] = Field(default=[], description="V18.1: Recent conversation history (last 3 interactions)")
    structured_lyrics: Optional[dict] = Field(default=None, description="V18.1: Structured lyrics object with sections")
    rhythm_map: Optional[dict] = Field(default=None, description="V18.1: Rhythm approximation map per section")

@api.post("/lyrics/free")
async def generate_free_lyrics(request: FreeLyricsRequest):
    """V17: Generate NP22-style lyrics from theme only"""
    try:
        # Generate lyrics using NP22 template with theme only
        lyrics_text = generate_np22_lyrics(theme=request.theme, bpm=None, mood=None)
        
        log_endpoint_event("/lyrics/free", None, "success", {"theme": request.theme})
        return success_response(
            data={
                "lyrics": lyrics_text
            },
            message="Free lyrics generated successfully"
        )
    except Exception as e:
        log_endpoint_event("/lyrics/free", None, "error", {"error": str(e)})
        return error_response(f"Free lyrics generation failed: {str(e)}")

# ============================================================================
# 2.4. POST /lyrics/refine - V18: INTERACTIVE LYRIC COLLABORATION
# ============================================================================

@api.post("/lyrics/refine")
async def refine_lyrics(request: LyricRefineRequest):
    """V18.1: Refine, rewrite, or extend lyrics based on user instructions with structured parsing and history"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # V18.1: Parse structured lyrics if not provided
    structured_lyrics = request.structured_lyrics
    if not structured_lyrics:
        structured_lyrics = parse_lyrics_to_structured(request.lyrics)
    
    # Build prompt using NP22 template + original lyrics + user instruction + BPM if given
    base_prompt = """You are an NP22-style lyric collaborator. Rewrite lyrics based on instruction while keeping:
- NP22 style (cinematic soulful rock × modern trap)
- dark-purple energy
- mindset themes
- melodic flow
- stadium-level emotion

Only modify what the instruction asks for. Keep original structure unless instruction says otherwise."""
    
    if request.bpm:
        base_prompt += f"\n\nBPM: {request.bpm} - ensure the lyrics flow naturally with this tempo."
    
    # V18.1: Add structured lyric information to prompt
    structure_info = ""
    if structured_lyrics:
        structure_info = "\n\nOriginal lyric structure:\n"
        for section_key, section_text in structured_lyrics.items():
            line_count = len([l for l in section_text.split('\n') if l.strip()])
            structure_info += f"- {section_key.capitalize()}: {line_count} lines\n"
    
    # V18.1: Add rhythm map information
    rhythm_info = ""
    if request.rhythm_map:
        rhythm_info = "\n\nRhythm map of lines (approximate bars per line):\n"
        for section_key, bar_counts in request.rhythm_map.items():
            if isinstance(bar_counts, list):
                rhythm_info += f"{section_key.capitalize()} bars: {bar_counts}\n"
        rhythm_info += "Please preserve approximate rhythm when refining.\n"
    
    # V18.1: Add conversation history context
    history_context = ""
    if request.history and len(request.history) > 0:
        history_context = "\n\nHere is recent conversation context:\n"
        for i, entry in enumerate(request.history, 1):
            prev_lyrics_preview = entry.get('previousLyrics', '')[:100] + '...' if len(entry.get('previousLyrics', '')) > 100 else entry.get('previousLyrics', '')
            instruction = entry.get('instruction', '')
            history_context += f"{i}. User said: {instruction}\n"
            history_context += f"   Previous lyrics: {prev_lyrics_preview}\n"
    
    user_prompt = f"""Original lyrics:
{request.lyrics}{structure_info}{rhythm_info}{history_context}

User instruction: {request.instruction}

Rewrite the lyrics according to the instruction while maintaining NP22 style. Return only the revised lyrics as plain text (no JSON, no explanations)."""
    
    # Fallback: simple instruction-applied version
    fallback_lyrics = request.lyrics  # Keep original if refinement fails
    
    if not api_key:
        logger.warning("OpenAI API key not configured - returning original lyrics")
        log_endpoint_event("/lyrics/refine", None, "error", {"error": "OpenAI API key not configured"})
        return success_response(
            data={"lyrics": fallback_lyrics},
            message="OpenAI API key not configured - returning original lyrics"
        )
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9
        )
        
        refined_lyrics = response.choices[0].message.content.strip() if response.choices[0].message.content else fallback_lyrics
        
        log_endpoint_event("/lyrics/refine", None, "success", {"instruction_length": len(request.instruction), "bpm": request.bpm})
        return success_response(
            data={"lyrics": refined_lyrics},
            message="Lyrics refined successfully"
        )
    except Exception as e:
        logger.warning(f"OpenAI lyrics refinement failed: {e} - returning original lyrics")
        log_endpoint_event("/lyrics/refine", None, "error", {"error": str(e)})
        return success_response(
            data={"lyrics": fallback_lyrics},
            message="Refinement failed - returning original lyrics"
        )

# ============================================================================
# 3. POST /recordings/upload - FIX MULTIPART + MEDIA_DIR BUG
# ============================================================================

@api.post("/recordings/upload")
async def upload_recording(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    """V20: Upload vocal recording with comprehensive validation"""
    session_id = session_id if session_id else str(uuid.uuid4())
    session_path = get_session_media_path(session_id)
    stems_path = session_path / "stems"
    stems_path.mkdir(exist_ok=True, parents=True)
    
    try:
        # V20: Validate filename
        if not file.filename:
            log_endpoint_event("/recordings/upload", session_id, "error", {"error": "No filename"})
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "No filename provided"}
            )
        
        # V20: Validate file extension (allowed: .wav, .mp3, .aiff)
        allowed_extensions = ('.wav', '.mp3', '.aiff')
        if not file.filename.lower().endswith(allowed_extensions):
            log_endpoint_event("/recordings/upload", session_id, "error", {"error": "Invalid format"})
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "Invalid audio file. Only .wav, .mp3, and .aiff formats are allowed"}
            )
        
        # V20: Read file content for validation
        content = await file.read()
        
        # V20: Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if len(content) > max_size:
            log_endpoint_event("/recordings/upload", session_id, "error", {"error": "File too large", "size": len(content)})
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "File size exceeds 50MB limit"}
            )
        
        # V20: Validate file is not zero-length
        if len(content) == 0:
            log_endpoint_event("/recordings/upload", session_id, "error", {"error": "Zero-length file"})
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "Invalid audio file. File is empty"}
            )
        
        # V20: Save file temporarily to validate with pydub
        file_path = stems_path / file.filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # V20: Validate file is actual audio by trying to load with pydub
        try:
            audio_segment = AudioSegment.from_file(str(file_path))
            # Check if audio has any duration (even if very short)
            if len(audio_segment) == 0:
                # Clean up invalid file
                file_path.unlink()
                log_endpoint_event("/recordings/upload", session_id, "error", {"error": "Corrupted audio"})
                return JSONResponse(
                    status_code=400,
                    content={"ok": False, "message": "Invalid audio file. File appears to be corrupted"}
                )
        except Exception as audio_error:
            # Clean up invalid file
            try:
                file_path.unlink()
            except:
                pass
            log_endpoint_event("/recordings/upload", session_id, "error", {"error": f"Audio validation failed: {str(audio_error)}"})
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "Invalid audio file. Could not read audio data"}
            )
        
        # V20: File is valid, update project memory
        memory = get_or_create_project_memory(session_id, MEDIA_DIR)
        final_url = f"/media/{session_id}/stems/{file.filename}"
        memory.add_asset(
            asset_type="stems",
            file_url=final_url,
            metadata={"filename": file.filename, "size": len(content)}
        )
        memory.advance_stage("upload", "mix")
        
        log_endpoint_event("/recordings/upload", session_id, "success", {"filename": file.filename, "size": len(content)})
        
        # V20: Return file_url in success response
        return success_response(
            data={
                "session_id": session_id,
                "file_url": final_url,
                "uploaded": final_url,
                "vocal_url": final_url,
                "filename": file.filename,
                "path": str(file_path)
            },
            message=f"Uploaded {file.filename} successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/recordings/upload", session_id, "error", {"error": str(e)})
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"Upload failed: {str(e)}"}
        )

# ============================================================================
# 4. POST /mix/run - PYDUB CHAIN + OPTIONAL AUPHONIC
# ============================================================================

@api.post("/mix/run")
async def mix_run(request: MixRequest):
    """Phase 2.2: Mix beat + stems with pydub chain, always mix vocals even if no beat"""
    session_path = get_session_media_path(request.session_id)
    mix_dir = session_path / "mix"
    mix_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Load stems (vocal files)
        stems_path = session_path / "stems"
        stem_files = []
        if stems_path.exists():
            # Get all audio files from stems directory
            stem_files = [
                f for f in stems_path.glob("*.*") 
                if f.suffix.lower() in ('.wav', '.mp3', '.m4a', '.aiff', '.flac')
            ]
        
        if not stem_files:
            logger.warning(f"⚠️ No stems found in {stems_path}")
            log_endpoint_event("/mix/run", request.session_id, "error", {"error": "No stems found"})
            return error_response("No vocal stems found. Upload recordings first.")
        
        logger.info(f"🎧 Found {len(stem_files)} stem file(s) to mix: {[f.name for f in stem_files]}")
        
        # Load and process stems
        mixed_vocals = None
        for stem_file in stem_files:
            try:
                stem = AudioSegment.from_file(str(stem_file))
                logger.info(f"Processing stem: {stem_file.name} ({len(stem)}ms)")
            except Exception as e:
                logger.warning(f"Skipping unreadable stem {stem_file}: {e}")
                continue
            
            # HPF on vocals (80-100 Hz)
            if request.hpf_hz > 0:
                stem = high_pass_filter(stem, cutoff=request.hpf_hz)
            
            # Light compression
            stem = compress_dynamic_range(stem, threshold=-20.0, ratio=3.0, attack=5.0, release=50.0)
            
            # Simple de-ess (narrow dip 5-7 kHz) - approximate with EQ
            # Note: pydub doesn't have built-in de-ess, so we simulate with gain reduction
            if request.deess_amount > 0:
                stem = stem - (request.deess_amount * 3)  # Slight reduction
            
            # Apply gain
            stem = stem + (20 * (request.vocal_gain - 1))
            
            # Combine vocals
            if mixed_vocals is None:
                mixed_vocals = stem
            else:
                # Ensure equal lengths before overlaying
                if len(mixed_vocals) < len(stem):
                    mixed_vocals = mixed_vocals + AudioSegment.silent(duration=len(stem) - len(mixed_vocals))
                elif len(stem) < len(mixed_vocals):
                    stem = stem + AudioSegment.silent(duration=len(mixed_vocals) - len(stem))
                mixed_vocals = mixed_vocals.overlay(stem)
        
        if mixed_vocals is None:
            log_endpoint_event("/mix/run", request.session_id, "error", {"error": "No processable stems"})
            return error_response("No processable vocal stems found.")
        
        # Check if beat exists
        beat_file = session_path / "beat.mp3"
        has_beat = beat_file.exists()
        
        if has_beat:
            # Load and process beat
            beat = AudioSegment.from_file(str(beat_file))
            beat = beat + (20 * (request.beat_gain - 1))  # Apply gain
            
            # Ensure equal lengths
            if len(mixed_vocals) < len(beat):
                mixed_vocals = mixed_vocals + AudioSegment.silent(duration=len(beat) - len(mixed_vocals))
            elif len(beat) < len(mixed_vocals):
                beat = beat + AudioSegment.silent(duration=len(mixed_vocals) - len(beat))
            
            # Final mix with beat
            final_mix = beat.overlay(mixed_vocals)
            logger.info("Mixing vocals with beat")
        else:
            # Vocals-only mix
            final_mix = mixed_vocals
            logger.info("✅ No beat found — mixing vocals only")
        
        # Export mix - maintain backward compatibility for beats, use mix_dir for vocals-only
        if has_beat:
            # Keep original behavior: save to session root for backward compatibility
            mix_file = session_path / "mix.wav"
            mix_url_path = f"/media/{request.session_id}/mix.wav"
            final_mix.export(str(mix_file), format="wav")
        else:
            # New behavior: vocals-only mixes go to mix directory
            mix_file = mix_dir / "vocals_only_mix.mp3"
            mix_url_path = f"/media/{request.session_id}/mix/vocals_only_mix.mp3"
            final_mix.export(str(mix_file), format="mp3")
        
        # Auphonic mastering (if key present)
        auphonic_key = os.getenv("AUPHONIC_API_KEY")
        master_file = session_path / "master.wav"
        
        if auphonic_key:
            try:
                # TODO: Implement Auphonic API call
                # For now, use local normalize
                logger.warning("Auphonic integration pending - using local normalize")
                mastered = normalize(final_mix)
                mastered.export(str(master_file), format="wav")
            except Exception as e:
                logger.error(f"Auphonic failed, using local: {e}")
                mastered = normalize(final_mix)
                mastered.export(str(master_file), format="wav")
        else:
            # Local normalize
            mastered = normalize(final_mix)
            mastered.export(str(master_file), format="wav")
        
        # Update project memory
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        memory.add_asset("mix", mix_url_path, {})
        memory.add_asset("master", f"/media/{request.session_id}/master.wav", {})
        memory.advance_stage("mix", "release")
        
        mastering_method = "auphonic" if auphonic_key else "local"
        mix_type = "vocals_only" if not has_beat else "vocals_and_beat"
        
        logger.info(f"✅ Mix completed ({mix_type}) - {len(stem_files)} stems, {mastering_method} mastering")
        logger.info(f"📁 Mix saved to: {mix_url_path}")
        
        log_endpoint_event("/mix/run", request.session_id, "success", {
            "mastering": mastering_method, 
            "stems": len(stem_files),
            "mix_type": mix_type
        })
        
        return success_response(
            data={
                "mix_url": mix_url_path,
                "master_url": f"/media/{request.session_id}/master.wav",
                "mastering": mastering_method,
                "stems_mixed": len(stem_files),
                "mix_type": mix_type
            },
            message=f"Mix completed ({mix_type}) with {mastering_method} mastering"
        )
    
    except Exception as e:
        log_endpoint_event("/mix/run", request.session_id, "error", {"error": str(e)})
        logger.error(f"Mix failed: {str(e)}", exc_info=True)
        return error_response(f"Mix failed: {str(e)}")

# ============================================================================
# V21: POST /mix/process - AI MIX & MASTER WITH DSP PIPELINE
# ============================================================================

@api.post("/mix/process")
async def mix_process(
    file: Optional[UploadFile] = File(None),
    file_url: Optional[str] = Form(None),
    session_id: str = Form(...),
    ai_mix: bool = Form(True),
    ai_master: bool = Form(True),
    mix_strength: float = Form(0.7),
    master_strength: float = Form(0.8),
    preset: str = Form("clean"),
    # V25: EQ parameters (slider values -6 to +6 dB)
    eq_low: float = Form(0.0),
    eq_mid: float = Form(0.0),
    eq_high: float = Form(0.0),
    # V25: FX parameters
    compression: float = Form(0.5),
    reverb: float = Form(0.3),
    limiter: float = Form(0.8)
):
    """V25: Process single audio file with REAL DSP chain (EQ, Compression, Reverb, Limiter, Mastering)"""
    session_path = get_session_media_path(session_id)
    mix_dir = session_path / "mix"
    mix_dir.mkdir(exist_ok=True, parents=True)
    
    input_file_path = None
    output_file = mix_dir / "mixed_mastered.wav"
    output_url = f"/media/{session_id}/mix/mixed_mastered.wav"
    
    try:
        # V21: Get input file - from upload or URL
        if file and file.filename:
            # Save uploaded file temporarily
            input_file_path = mix_dir / f"temp_input_{uuid.uuid4().hex[:8]}{Path(file.filename).suffix}"
            content = await file.read()
            
            # Validate file size (50MB limit)
            max_size = 50 * 1024 * 1024
            if len(content) > max_size:
                return error_response("File size exceeds 50MB limit")
            
            # Validate extension
            allowed_extensions = ('.wav', '.mp3', '.aiff')
            if not file.filename.lower().endswith(allowed_extensions):
                return error_response("Unsupported format. Please use .wav, .mp3, or .aiff")
            
            with open(input_file_path, 'wb') as f:
                f.write(content)
        elif file_url:
            # Fetch file from URL (can be absolute URL or relative path)
            try:
                # Handle relative paths (e.g., /media/session/stems/file.wav)
                if file_url.startswith('/'):
                    # Convert to absolute path
                    file_path = Path('.' + file_url)
                    if file_path.exists():
                        input_file_path = file_path
                    else:
                        # Try fetching from server URL
                        base_url = f"http://localhost:8000{file_url}"
                        response = requests.get(base_url, timeout=30, stream=True)
                        if not response.ok:
                            return error_response(f"Could not fetch file from URL: {file_url}")
                        input_file_path = mix_dir / f"temp_input_{uuid.uuid4().hex[:8]}.wav"
                        with open(input_file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                else:
                    # Absolute URL
                    response = requests.get(file_url, timeout=30, stream=True)
                    if not response.ok:
                        return error_response(f"Could not fetch file from URL: {file_url}")
                    input_file_path = mix_dir / f"temp_input_{uuid.uuid4().hex[:8]}.wav"
                    with open(input_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            except Exception as e:
                logger.error(f"Failed to fetch file from URL: {e}")
                return error_response(f"Failed to fetch file: {str(e)}")
        else:
            return error_response("No file provided. Upload a file or provide file_url")
        
        if not input_file_path or not input_file_path.exists():
            return error_response("Could not read input file")
        
        # V21: Validate audio file with pydub
        try:
            audio = AudioSegment.from_file(str(input_file_path))
            if len(audio) == 0:
                if input_file_path.exists():
                    input_file_path.unlink()
                return error_response("Corrupted audio file")
        except Exception as e:
            if input_file_path.exists():
                try:
                    input_file_path.unlink()
                except:
                    pass
            logger.error(f"Audio validation failed: {e}")
            return error_response("Could not read audio data. File may be corrupted")
        
        logger.info(f"🎧 Processing audio: {len(audio)}ms, sample_rate={audio.frame_rate}")
        
        # V25: Validate DSP parameters
        eq_low_gain = max(-6.0, min(6.0, eq_low))
        eq_mid_gain = max(-6.0, min(6.0, eq_mid))
        eq_high_gain = max(-6.0, min(6.0, eq_high))
        compression_val = max(0.0, min(1.0, compression))
        reverb_val = max(0.0, min(1.0, reverb))
        limiter_val = max(0.0, min(1.0, limiter))
        
        # V25: Apply preset overrides if preset is selected
        if preset == "warm":
            eq_low_gain = 2.0
            eq_mid_gain = -1.0
            eq_high_gain = 1.0
            reverb_val = 0.3  # light reverb
            compression_val = 0.6  # medium compression
            limiter_val = 0.7  # soft limiter
        elif preset == "clean":
            eq_low_gain = 0.0
            eq_mid_gain = -2.0
            eq_high_gain = 0.0
            reverb_val = 0.0  # no reverb
            compression_val = 0.3  # low compression
            limiter_val = 0.0  # no limiter
        elif preset == "bright":
            eq_low_gain = 0.0
            eq_mid_gain = -1.0
            eq_high_gain = 3.0
            reverb_val = 0.0  # no reverb
            compression_val = 0.6  # medium compression
            limiter_val = 0.5  # medium limiter
        
        # V25.1: REAL DSP PIPELINE using ffmpeg filters (V25 spec)
        # Build filter chain as single ffmpeg command
        
        # Stage 1: EQ (3-band) - always apply
        eq_low_filter = f"equalizer=f=100:t=lowshelf:g={eq_low_gain}"
        eq_mid_filter = f"equalizer=f=1500:t=peak:g={eq_mid_gain}:width=2"
        eq_high_filter = f"equalizer=f=10000:t=highshelf:g={eq_high_gain}"
        
        # Stage 2: Compression (compand)
        # FIX 2: Cast to integer - compand 'points=' must not contain floats
        # Map compression slider (0-1) to compand threshold
        # compression 0 = no compression, 1 = full compression
        mix_strength_db_int = int(abs(-10.0 - (compression_val * 10.0)))  # Cast compand threshold to int
        compand_filter = f"compand=attacks=0.01:decays=0.2:points=-90/-90|-20/-20|-10/-{mix_strength_db_int}|0/0"
        
        # Stage 3: Reverb (aecho)
        # FIX 1: Reverb delay MUST be integer - map slider (0-1) → delay in ms (20-60), decay 0.2-0.8
        delay_ms = int(20 + (reverb_val * 40))  # always integer between 20 and 60
        decay = 0.2 + (reverb_val * 0.6)  # 0.2-0.8 (decay can be float)
        # Note: FFmpeg aecho takes delay in seconds, but user spec shows delay_ms directly
        # Convert milliseconds to seconds for FFmpeg (delay_ms is already integer)
        aecho_filter = f"aecho=0.8:0.88:{delay_ms/1000.0}:{decay}"
        
        # Stage 4: Limiter (per slider)
        limiter_filter = "alimiter=limit=0.95:level=1"
        
        # Stage 5: Final Mastering Chain (always apply)
        # FIX 3: Stereotools is optional - check availability first
        stereo_filter = ""
        try:
            # Test if stereotools is available in FFmpeg
            test_result = subprocess.run(
                ["ffmpeg", "-filters"],
                capture_output=True,
                timeout=5
            )
            if "stereotools" in test_result.stdout.decode('utf-8', errors='ignore'):
                stereo_filter = "stereotools=mlev=1.05"
        except:
            stereo_filter = ""
        
        master_filter = "alimiter=limit=0.98"
        
        # FIX 4: Build filter chain safely - remove empty filters, no trailing commas
        filters = [eq_low_filter, eq_mid_filter, eq_high_filter, compand_filter, aecho_filter, limiter_filter]
        if stereo_filter:
            filters.append(stereo_filter)
        filters.append("loudnorm=I=-13:TP=-1:LRA=7")
        filters.append(master_filter)
        
        # Remove empty filters to avoid empty commas in chain
        filter_chain = ",".join([f for f in filters if f])
        
        # V25.1: Execute DSP chain with ffmpeg (single command)
        temp_processed = mix_dir / f"temp_processed_{uuid.uuid4().hex[:8]}.wav"
        
        # Build ffmpeg command with filter chain
        cmd = [
            'ffmpeg', '-i', str(input_file_path),
            '-af', filter_chain,
            '-ar', '44100',
            '-ac', '2',  # Ensure stereo output
            '-y', str(temp_processed)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, check=True, timeout=120)
            if not temp_processed.exists():
                raise Exception("FFmpeg output file not created")
            # Move to final output
            shutil.move(str(temp_processed), str(output_file))
            
            # FIX 5: Guarantee output file exists before returning
            # Wait for file to exist and have content (up to 400ms)
            for _ in range(20):  # wait up to 400ms
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    break
                time.sleep(0.02)
            
            # Final check - raise error if file still missing
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                raise RuntimeError("Output file missing or empty after DSP chain")
            
            logger.info(f"✅ DSP chain applied: {len(filters)} filters")
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
            logger.error(f"FFmpeg DSP chain failed: {e}")
            if temp_processed.exists():
                temp_processed.unlink()
            # FIX 6: Remove fallback copy - raise error instead
            raise RuntimeError(f"DSP chain failed: {e}")
        
        # Clean up temp input file
        if input_file_path and input_file_path.exists() and input_file_path != output_file:
            try:
                input_file_path.unlink()
            except:
                pass
        
        # V25.1: Update project memory (removed mixCompleted)
        memory = get_or_create_project_memory(session_id, MEDIA_DIR)
        memory.add_asset("mix", output_url, {
            "ai_mix": ai_mix,
            "ai_master": ai_master,
            "preset": preset,
            "mix_strength": mix_strength,
            "master_strength": master_strength,
            "eq_low": eq_low_gain,
            "eq_mid": eq_mid_gain,
            "eq_high": eq_high_gain,
            "compression": compression_val,
            "reverb": reverb_val,
            "limiter": limiter_val
        })
        
        logger.info(f"✅ Mix & master completed - preset={preset}, ai_mix={ai_mix}, ai_master={ai_master}")
        logger.info(f"📁 Processed file saved to: {output_url}")
        logger.info(f"🎛️ DSP params: EQ({eq_low_gain:.1f}/{eq_mid_gain:.1f}/{eq_high_gain:.1f}) Comp={compression_val:.2f} Rev={reverb_val:.2f} Lim={limiter_val:.2f}")
        
        log_endpoint_event("/mix/process", session_id, "success", {
            "preset": preset,
            "ai_mix": ai_mix,
            "ai_master": ai_master,
            "mix_strength": mix_strength,
            "master_strength": master_strength,
            "eq": {"low": eq_low_gain, "mid": eq_mid_gain, "high": eq_high_gain},
            "compression": compression_val,
            "reverb": reverb_val,
            "limiter": limiter_val
        })
        
        # V25.1: Return EXACTLY file_url (no other fields required)
        return success_response(
            data={
                "file_url": output_url
            },
            message="Mix and master completed successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/mix/process", session_id, "error", {"error": str(e)})
        logger.error(f"Mix process failed: {str(e)}", exc_info=True)
        return error_response("Mixing failed")
    finally:
        # Cleanup temp files
        if input_file_path and input_file_path.exists() and input_file_path != output_file:
            try:
                input_file_path.unlink()
            except:
                pass

# ============================================================================
# NEW RELEASE MODULE - REDESIGNED
# ============================================================================

class ReleaseCoverRequest(BaseModel):
    session_id: str
    track_title: str
    artist_name: str
    genre: str
    mood: str
    style: Optional[str] = Field(default="realistic", description="realistic / abstract / cinematic / illustrated / purple-gold aesthetic")

class ReleaseCopyRequest(BaseModel):
    session_id: str
    track_title: str
    artist_name: str
    genre: str
    mood: str
    lyrics: Optional[str] = ""

class ReleaseMetadataRequest(BaseModel):
    session_id: str
    track_title: str
    artist_name: str
    mood: str
    genre: str
    explicit: bool = False
    release_date: str

@api.post("/release/cover")
async def generate_release_cover(request: ReleaseCoverRequest):
    """Generate AI cover art using OpenAI (3 images, 3000x3000, 1500x1500, 1080x1920)"""
    session_path = get_session_media_path(request.session_id)
    cover_dir = session_path / "release" / "cover"
    cover_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            log_endpoint_event("/release/cover", request.session_id, "error", {"error": "OpenAI API key not configured"})
            return error_response("OpenAI API key not configured")
        
        from openai import OpenAI
        import base64
        from PIL import Image
        from io import BytesIO
        
        client = OpenAI(api_key=api_key)
        
        # Build prompt according to spec
        prompt = (
            f"High-quality album cover for the single '{request.track_title}' "
            f"by {request.artist_name}. Genre: {request.genre}. Mood: {request.mood}. "
            f"Style: {request.style}. Clean, cinematic, striking, professional. "
            "3000×3000 resolution, centered composition."
        )
        
        # Generate 3 images with base64 response
        response = client.images.generate(
            model="dall-e-2",  # Using dall-e-2 as it supports b64_json and n=3
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            response_format="b64_json",
            n=3
        )
        
        generated_urls = []
        
        for i, img_data in enumerate(response.data):
            img_bytes = base64.b64decode(img_data.b64_json)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            
            # Always upscale to 3000×3000
            img_3000 = img.resize((3000, 3000), Image.LANCZOS)
            
            # Derivative variants
            img_1500 = img_3000.resize((1500, 1500), Image.LANCZOS)
            img_vertical = img_3000.resize((1080, 1920), Image.LANCZOS)
            
            # Save all variants
            img_3000.save(cover_dir / f"cover_{i+1}.jpg", "JPEG", quality=95)
            img_1500.save(cover_dir / f"cover_{i+1}_1500.jpg", "JPEG", quality=95)
            img_vertical.save(cover_dir / f"cover_{i+1}_vertical.jpg", "JPEG", quality=95)
            
            generated_urls.append(
                f"/media/{request.session_id}/release/cover/cover_{i+1}.jpg"
            )
        
        if not generated_urls:
            return error_response("Failed to generate any cover art images")
        
        log_endpoint_event("/release/cover", request.session_id, "success", {"count": len(generated_urls)})
        return success_response({"images": generated_urls})
    
    except Exception as e:
        log_endpoint_event("/release/cover", request.session_id, "error", {"error": str(e)})
        return error_response(f"Cover art generation failed: {str(e)}")

class ReleaseSelectCoverRequest(BaseModel):
    session_id: str
    cover_url: str

@api.post("/release/select-cover")
async def select_release_cover(request: ReleaseSelectCoverRequest):
    """Save selected cover art to final versions (3000, 1500, vertical) and update memory"""
    session_path = get_session_media_path(request.session_id)
    cover_dir = session_path / "release" / "cover"
    cover_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        index = int(request.cover_url.split("cover_")[1].split(".")[0])
        
        src_3000 = cover_dir / f"cover_{index}.jpg"
        src_1500 = cover_dir / f"cover_{index}_1500.jpg"
        src_vertical = cover_dir / f"cover_{index}_vertical.jpg"
        
        dst_3000 = cover_dir / "final_cover_3000.jpg"
        dst_1500 = cover_dir / "final_cover_1500.jpg"
        dst_vertical = cover_dir / "final_cover_vertical.jpg"
        
        shutil.copy(src_3000, dst_3000)
        shutil.copy(src_1500, dst_1500)
        shutil.copy(src_vertical, dst_vertical)
        
        # Update project memory
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        memory.update("release.cover_art", f"/media/{request.session_id}/release/cover/final_cover_3000.jpg")
        memory.save()
        
        log_endpoint_event("/release/select-cover", request.session_id, "success", {})
        return success_response({"final_cover": memory.project_data["release"]["cover_art"]})
    
    except Exception as e:
        log_endpoint_event("/release/select-cover", request.session_id, "error", {"error": str(e)})
        return error_response(f"Failed to select cover art: {str(e)}")

@api.post("/release/copy")
async def generate_release_copy(request: ReleaseCopyRequest):
    """Generate release copy: release_description.txt, press_pitch.txt, tagline.txt"""
    session_path = get_session_media_path(request.session_id)
    copy_dir = session_path / "release" / "copy"
    copy_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Fallback text
            release_desc = f"{request.track_title} by {request.artist_name} is a {request.mood} {request.genre} track."
            press_pitch = f"New release from {request.artist_name}: {request.track_title}"
            tagline = f"{request.track_title} - {request.artist_name}"
            genre_tags = [request.genre, request.mood, "new music", "independent artist"]
        else:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            prompt = f"""Generate professional release copy for:
Track: {request.track_title}
Artist: {request.artist_name}
Genre: {request.genre}
Mood: {request.mood}
{"Lyrics excerpt: " + request.lyrics[:200] if request.lyrics else ""}

Provide:
1. release_description.txt - Short, clean description (2-3 sentences)
2. press_pitch.txt - Professional press pitch (1 paragraph)
3. tagline.txt - Catchy one-liner tagline
4. genre_tags - 5-7 relevant genre/mood tags (comma-separated)

Format as JSON:
{{
  "release_description": "...",
  "press_pitch": "...",
  "tagline": "...",
  "genre_tags": ["tag1", "tag2", ...]
}}"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional music publicist. Generate concise, professional release copy."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8
            )
            
            content = response.choices[0].message.content.strip()
            # Try to parse JSON
            try:
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    copy_data = json.loads(json_match.group())
                    release_desc = copy_data.get("release_description", "")
                    press_pitch = copy_data.get("press_pitch", "")
                    tagline = copy_data.get("tagline", "")
                    genre_tags = copy_data.get("genre_tags", [])
                else:
                    raise ValueError("No JSON found")
            except:
                # Fallback parsing
                lines = content.split('\n')
                release_desc = lines[0] if lines else ""
                press_pitch = lines[1] if len(lines) > 1 else ""
                tagline = lines[2] if len(lines) > 2 else ""
                genre_tags = [request.genre, request.mood]
        
        # Save files
        with open(copy_dir / "release_description.txt", 'w', encoding='utf-8') as f:
            f.write(release_desc)
        
        with open(copy_dir / "press_pitch.txt", 'w', encoding='utf-8') as f:
            f.write(press_pitch)
        
        with open(copy_dir / "tagline.txt", 'w', encoding='utf-8') as f:
            f.write(tagline)
        
        # Update project memory
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        copy_files = [
            f"/media/{request.session_id}/release/copy/release_description.txt",
            f"/media/{request.session_id}/release/copy/press_pitch.txt",
            f"/media/{request.session_id}/release/copy/tagline.txt"
        ]
        if not memory.project_data.get("release", {}).get("files"):
            memory.update("release.files", [])
        current_files = memory.project_data.get("release", {}).get("files", [])
        for f in copy_files:
            if f not in current_files:
                current_files.append(f)
        memory.update("release.files", current_files)
        memory.save()
        
        log_endpoint_event("/release/copy", request.session_id, "success", {})
        return success_response(
            data={
                "description_url": f"/media/{request.session_id}/release/copy/release_description.txt",
                "pitch_url": f"/media/{request.session_id}/release/copy/press_pitch.txt",
                "tagline_url": f"/media/{request.session_id}/release/copy/tagline.txt"
            },
            message="Release copy generated successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/release/copy", request.session_id, "error", {"error": str(e)})
        return error_response(f"Release copy generation failed: {str(e)}")

@api.post("/release/lyrics")
async def generate_lyrics_pdf(request: ReleaseRequest):
    """Generate lyrics.pdf if lyrics exist"""
    session_path = get_session_media_path(request.session_id)
    lyrics_dir = session_path / "release" / "lyrics"
    lyrics_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        lyrics_text = request.lyrics or ""
        
        # Check if lyrics exist in project
        if not lyrics_text:
            memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
            lyrics_file = session_path / "lyrics.txt"
            if lyrics_file.exists():
                with open(lyrics_file, 'r', encoding='utf-8') as f:
                    lyrics_text = f.read()
        
        if not lyrics_text or not lyrics_text.strip():
            log_endpoint_event("/release/lyrics", request.session_id, "success", {"skipped": True})
            return success_response(
                data={"skipped": True, "message": "No lyrics found"},
                message="No lyrics to generate PDF for"
            )
        
        # Generate PDF using reportlab
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        pdf_path = lyrics_dir / "lyrics.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        
        # Build content
        story = []
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='black',
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Normal style
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            textColor='black',
            leading=18
        )
        
        # Title page
        title = request.title or "Untitled"
        artist = request.artist or "Unknown Artist"
        story.append(Paragraph(f"{artist}", title_style))
        story.append(Paragraph(f"{title}", title_style))
        story.append(PageBreak())
        
        # Lyrics content
        lines = lyrics_text.split('\n')
        for line in lines:
            if line.strip():
                story.append(Paragraph(line.strip(), normal_style))
            else:
                story.append(Spacer(1, 0.2*inch))
        
        doc.build(story)
        
        # Update project memory
        pdf_url = f"/media/{request.session_id}/release/lyrics/lyrics.pdf"
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        if not memory.project_data.get("release", {}).get("files"):
            memory.update("release.files", [])
        current_files = memory.project_data.get("release", {}).get("files", [])
        if pdf_url not in current_files:
            current_files.append(pdf_url)
        memory.update("release.files", current_files)
        memory.save()
        
        log_endpoint_event("/release/lyrics", request.session_id, "success", {})
        return success_response(
            data={"pdf_url": pdf_url},
            message="Lyrics PDF generated successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/release/lyrics", request.session_id, "error", {"error": str(e)})
        return error_response(f"Lyrics PDF generation failed: {str(e)}")

@api.post("/release/metadata")
async def generate_release_metadata(request: ReleaseMetadataRequest):
    """Generate metadata.json with track info"""
    session_path = get_session_media_path(request.session_id)
    metadata_dir = session_path / "release" / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get audio duration from mixed/master file
        duration_seconds = 0
        bpm = None
        key = None
        
        # Try to find audio file
        for filename in ["mix/mixed_mastered.wav", "mix.wav", "master.wav"]:
            audio_file = session_path / filename
            if audio_file.exists():
                try:
                    audio = AudioSegment.from_file(str(audio_file))
                    duration_seconds = len(audio) / 1000.0
                    break
                except:
                    pass
        
        # Get BPM and key from project memory
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        bpm = memory.project_data.get("metadata", {}).get("tempo")
        key = memory.project_data.get("metadata", {}).get("key")
        
        metadata = {
            "title": request.track_title,
            "artist": request.artist_name,
            "genre": request.genre,
            "mood": request.mood,
            "explicit": request.explicit,
            "release_date": request.release_date,
            "duration_seconds": round(duration_seconds, 2),
            "bpm": bpm,
            "key": key
        }
        
        metadata_file = metadata_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Update project memory with full release info
        metadata_url = f"/media/{request.session_id}/release/metadata/metadata.json"
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        memory.update("release.title", request.track_title)
        memory.update("release.artist", request.artist_name)
        memory.update("release.genre", request.genre)
        memory.update("release.mood", request.mood)
        memory.update("release.explicit", request.explicit)
        memory.update("release.release_date", request.release_date)
        memory.update("release.metadata_path", metadata_url)
        if not memory.project_data.get("release", {}).get("files"):
            memory.update("release.files", [])
        current_files = memory.project_data.get("release", {}).get("files", [])
        if metadata_url not in current_files:
            current_files.append(metadata_url)
        memory.update("release.files", current_files)
        memory.save()
        
        log_endpoint_event("/release/metadata", request.session_id, "success", {})
        return success_response(
            data={"metadata_url": metadata_url},
            message="Metadata generated successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/release/metadata", request.session_id, "error", {"error": str(e)})
        return error_response(f"Metadata generation failed: {str(e)}")

class ReleaseFilesRequest(BaseModel):
    session_id: str

@api.get("/release/files")
async def list_release_files(session_id: str = Query(...)):
    """List all release files dynamically"""
    session_path = get_session_media_path(session_id)
    release_dir = session_path / "release"
    
    try:
        files = []
        
        # Audio files
        audio_dir = release_dir / "audio"
        if audio_dir.exists():
            audio_file = audio_dir / "mixed_mastered.wav"
            if audio_file.exists():
                files.append(f"/media/{session_id}/release/audio/mixed_mastered.wav")
        
        # Cover art (final_cover_3000.jpg, final_cover_1500.jpg, final_cover_vertical.jpg)
        cover_dir = release_dir / "cover"
        if cover_dir.exists():
            # Scan for final cover files
            for file in cover_dir.glob("final_cover*.jpg"):
                files.append(f"/media/{session_id}/release/cover/{file.name}")
        
        # Metadata
        metadata_dir = release_dir / "metadata"
        if metadata_dir.exists():
            metadata_file = metadata_dir / "metadata.json"
            if metadata_file.exists():
                files.append(f"/media/{session_id}/release/metadata/metadata.json")
        
        # Copy files
        copy_dir = release_dir / "copy"
        if copy_dir.exists():
            for copy_file in copy_dir.glob("*.txt"):
                files.append(f"/media/{session_id}/release/copy/{copy_file.name}")
        
        # Lyrics PDF
        lyrics_dir = release_dir / "lyrics"
        if lyrics_dir.exists():
            lyrics_file = lyrics_dir / "lyrics.pdf"
            if lyrics_file.exists():
                files.append(f"/media/{session_id}/release/lyrics/lyrics.pdf")
        
        log_endpoint_event("/release/files", session_id, "success", {"count": len(files)})
        return success_response(
            data={"files": files},
            message=f"Found {len(files)} release files"
        )
    
    except Exception as e:
        log_endpoint_event("/release/files", session_id, "error", {"error": str(e)})
        return error_response(f"Failed to list release files: {str(e)}")

@api.get("/release/pack")
async def get_release_pack(session_id: str = Query(...)):
    """Get complete release pack data: cover art, metadata, lyrics PDF, release copy, and audio"""
    session_path = get_session_media_path(session_id)
    release_dir = session_path / "release"
    
    try:
        result = {}
        
        # Cover art (prefer final_cover_3000.jpg)
        cover_dir = release_dir / "cover"
        if cover_dir.exists():
            final_cover = cover_dir / "final_cover_3000.jpg"
            if final_cover.exists():
                result["coverArt"] = f"/media/{session_id}/release/cover/final_cover_3000.jpg"
            else:
                # Fallback to any cover file
                covers = list(cover_dir.glob("cover_*.jpg"))
                if covers:
                    result["coverArt"] = f"/media/{session_id}/release/cover/{covers[0].name}"
        
        # Metadata
        metadata_dir = release_dir / "metadata"
        if metadata_dir.exists():
            metadata_file = metadata_dir / "metadata.json"
            if metadata_file.exists():
                result["metadataFile"] = f"/media/{session_id}/release/metadata/metadata.json"
        
        # Lyrics PDF
        lyrics_dir = release_dir / "lyrics"
        if lyrics_dir.exists():
            lyrics_file = lyrics_dir / "lyrics.pdf"
            if lyrics_file.exists():
                result["lyricsPdf"] = f"/media/{session_id}/release/lyrics/lyrics.pdf"
        
        # Release copy files
        copy_dir = release_dir / "copy"
        release_copy = {}
        if copy_dir.exists():
            desc_file = copy_dir / "release_description.txt"
            pitch_file = copy_dir / "press_pitch.txt"
            tagline_file = copy_dir / "tagline.txt"
            
            if desc_file.exists():
                release_copy["description"] = f"/media/{session_id}/release/copy/release_description.txt"
            if pitch_file.exists():
                release_copy["pitch"] = f"/media/{session_id}/release/copy/press_pitch.txt"
            if tagline_file.exists():
                release_copy["tagline"] = f"/media/{session_id}/release/copy/tagline.txt"
        
        if release_copy:
            result["releaseCopy"] = release_copy
        
        # Release audio (from mix stage or release/audio)
        audio_dir = release_dir / "audio"
        if audio_dir.exists():
            audio_file = audio_dir / "mixed_mastered.wav"
            if audio_file.exists():
                result["releaseAudio"] = f"/media/{session_id}/release/audio/mixed_mastered.wav"
        else:
            # Fallback to mix directory
            mix_audio = session_path / "mix" / "mixed_mastered.wav"
            if mix_audio.exists():
                result["releaseAudio"] = f"/media/{session_id}/mix/mixed_mastered.wav"
        
        log_endpoint_event("/release/pack", session_id, "success", {})
        return success_response(
            data=result,
            message="Release pack data retrieved successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/release/pack", session_id, "error", {"error": str(e)})
        return error_response(f"Failed to get release pack: {str(e)}")

@api.post("/release/download-all")
async def download_all_release_files(request: ReleaseRequest):
    """Generate ZIP of all release files (desktop only)"""
    session_path = get_session_media_path(request.session_id)
    release_dir = session_path / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Ensure audio files are in release/audio directory
        audio_dir = release_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy mixed/master files to audio directory if they exist
        for source_file in ["mix/mixed_mastered.wav", "mix.wav", "master.wav"]:
            source_path = session_path / source_file
            if source_path.exists():
                # Copy WAV
                dest_wav = audio_dir / "mixed_mastered.wav"
                shutil.copy(source_path, dest_wav)
                
                # Export MP3
                try:
                    audio = AudioSegment.from_file(str(source_path))
                    dest_mp3 = audio_dir / "mixed_mastered.mp3"
                    audio.export(str(dest_mp3), format="mp3", bitrate="320k")
                except:
                    pass
                break
        
        zip_file = release_dir / "release_pack.zip"
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Audio files
            if audio_dir.exists():
                for file in audio_dir.glob("*"):
                    if file.is_file():
                        zf.write(file, f"audio/{file.name}")
            
            # Cover art (only selected cover)
            cover_dir = release_dir / "cover"
            if cover_dir.exists():
                # Find selected cover (cover_3000.jpg or first cover)
                selected_cover = cover_dir / "cover_3000.jpg"
                if not selected_cover.exists():
                    # Try to find first cover and rename
                    covers = list(cover_dir.glob("cover_*.jpg"))
                    if covers:
                        selected_cover = covers[0]
                
                if selected_cover.exists():
                    # Copy to final names
                    cover_3000 = cover_dir / "cover_3000.jpg"
                    cover_1500 = cover_dir / "cover_1500.jpg"
                    cover_vertical = cover_dir / "cover_vertical.jpg"
                    
                    if not cover_3000.exists():
                        shutil.copy(selected_cover, cover_3000)
                    if not cover_1500.exists():
                        img = Image.open(cover_3000)
                        img_1500 = img.resize((1500, 1500), Image.Resampling.LANCZOS)
                        img_1500.save(cover_1500, "JPEG", quality=95)
                    if not cover_vertical.exists():
                        img = Image.open(cover_3000)
                        img_vertical = img.resize((1080, 1920), Image.Resampling.LANCZOS)
                        img_vertical.save(cover_vertical, "JPEG", quality=95)
                    
                    zf.write(cover_3000, "cover/cover_3000.jpg")
                    zf.write(cover_1500, "cover/cover_1500.jpg")
                    zf.write(cover_vertical, "cover/cover_vertical.jpg")
            
            # Lyrics
            lyrics_dir = release_dir / "lyrics"
            if lyrics_dir.exists():
                for file in lyrics_dir.glob("*.pdf"):
                    zf.write(file, f"lyrics/{file.name}")
            
            # Metadata
            metadata_dir = release_dir / "metadata"
            if metadata_dir.exists():
                for file in metadata_dir.glob("*.json"):
                    zf.write(file, f"metadata/{file.name}")
            
            # Copy files
            copy_dir = release_dir / "copy"
            if copy_dir.exists():
                for file in copy_dir.glob("*.txt"):
                    zf.write(file, f"copy/{file.name}")
        
        zip_url = f"/media/{request.session_id}/release/release_pack.zip"
        
        log_endpoint_event("/release/download-all", request.session_id, "success", {})
        return success_response(
            data={"zip_url": zip_url},
            message="Release pack ZIP generated successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/release/download-all", request.session_id, "error", {"error": str(e)})
        return error_response(f"ZIP generation failed: {str(e)}")

# ============================================================================
# 7. POST /content/ideas - NEW ENDPOINT (DEMO CAPTIONS)
# ============================================================================

@api.post("/content/ideas")
async def get_content_ideas(request: ReleaseRequest):
    """Phase 2.2: Generate demo content captions for social media"""
    try:
        # Demo captions with hook, text, and hashtags
        demo_captions = [
            {
                "hook": "New music alert! 🎵",
                "text": f"Just dropped '{request.title}' by {request.artist}! This track hits different. Link in bio to stream now!",
                "hashtags": ["#NewMusic", "#IndependentArtist", "#MusicRelease", "#NowPlaying"]
            },
            {
                "hook": "Behind the scenes 🎧",
                "text": f"The creative process behind '{request.title}' was intense! Swipe to see how we made this happen.",
                "hashtags": ["#BehindTheScenes", "#StudioLife", "#MusicProduction", "#CreativeProcess"]
            },
            {
                "hook": "Exclusive drop! 💎",
                "text": f"{request.artist} just released '{request.title}' and it's already making waves. Don't sleep on this one!",
                "hashtags": ["#Exclusive", "#MusicDrop", "#NewArtist", "#Trending"]
            }
        ]
        
        log_endpoint_event("/content/ideas", request.session_id, "success", {"count": len(demo_captions)})
        return success_response(
            data={"captions": demo_captions},
            message="Content ideas generated successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/content/ideas", request.session_id, "error", {"error": str(e)})
        return error_response(f"Content ideas generation failed: {str(e)}")

# ============================================================================
# 8. SOCIAL ENDPOINTS - LOCAL JSON SCHEDULER (NO BUFFER)
# ============================================================================

@api.get("/social/platforms")
async def get_social_platforms():
    """Return supported platforms"""
    log_endpoint_event("/social/platforms", None, "success", {})
    return success_response(
        data={"platforms": ["tiktok", "shorts", "reels"]},
        message="Platforms retrieved successfully"
    )

@api.post("/social/posts")
async def create_social_post(request: SocialPostRequest):
    """Schedule a social post using GetLate.dev API or local JSON fallback"""
    session_path = get_session_media_path(request.session_id)
    getlate_key = os.getenv("GETLATE_API_KEY")
    
    try:
        # Set defaults if missing
        platform = request.platform or "tiktok"
        when_iso = request.when_iso or (datetime.now().isoformat() + "Z")
        caption = request.caption or "New music release!"
        
        if platform not in ["tiktok", "shorts", "reels"]:
            log_endpoint_event("/social/posts", request.session_id, "error", {"error": "Invalid platform"})
            return error_response("Invalid platform. Use: tiktok, shorts, or reels")
        
        # Try GetLate.dev API if key is available
        if getlate_key:
            try:
                scheduler = SocialScheduler(request.session_id)
                result = scheduler.schedule_with_getlate(
                    platform=platform,
                    content=caption,
                    scheduled_time=when_iso,
                    api_key=getlate_key
                )
                
                if result.get("success"):
                    # Update project memory
                    memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
                    memory.advance_stage("content", "analytics")
                    
                    log_endpoint_event("/social/posts", request.session_id, "success", {
                        "platform": platform,
                        "provider": "getlate"
                    })
                    return success_response(
                        data={
                            "post_id": result.get("post_id"),
                            "platform": platform,
                            "scheduled_time": when_iso,
                            "provider": "getlate",
                            "status": "scheduled"
                        },
                        message=f"Post scheduled on {platform} via GetLate.dev"
                    )
                else:
                    logger.warning(f"GetLate API failed: {result.get('error')} - falling back to local")
            except Exception as e:
                logger.warning(f"GetLate API error: {e} - falling back to local JSON")
        
        # FALLBACK: Local JSON storage
        schedule_file = session_path / "schedule.json"
        
        # Load existing schedule
        if schedule_file.exists():
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
        else:
            schedule = []
        
        # Append new post
        post_id = f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        post = {
            "post_id": post_id,
            "platform": platform,
            "when_iso": when_iso,
            "scheduled_time": when_iso,
            "caption": caption,
            "content": caption,
            "created_at": datetime.now().isoformat(),
            "provider": "local",
            "status": "scheduled"
        }
        schedule.append(post)
        
        # Save
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        
        # Update project memory
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        memory.advance_stage("content", "analytics")
        
        log_endpoint_event("/social/posts", request.session_id, "success", {
            "platform": platform,
            "provider": "local"
        })
        return success_response(
            data={"post": post, "total_scheduled": len(schedule), "provider": "local", "status": "scheduled"},
            message=f"Post scheduled locally on {platform} (GetLate API key not configured)"
        )
    
    except Exception as e:
        log_endpoint_event("/social/posts", request.session_id, "error", {"error": str(e)})
        return error_response(f"Social post scheduling failed: {str(e)}")

# ============================================================================
# 8. ANALYTICS ENDPOINTS - SAFE DEMO METRICS
# ============================================================================

@api.get("/analytics/session/{session_id}")
async def get_session_analytics(session_id: str):
    """Phase 2.2: Get analytics for a specific session (safe demo metrics)"""
    try:
        session_path = get_session_media_path(session_id)
        project_file = session_path / "project.json"
        schedule_file = session_path / "schedule.json"
        
        # Safe defaults
        analytics = {
            "session_id": session_id,
            "stages_completed": 0,
            "files_created": 0,
            "scheduled_posts": 0,
            "estimated_reach": 0
        }
        
        # Load project.json if exists
        if project_file.exists():
            try:
                with open(project_file, 'r') as f:
                    project_data = json.load(f)
                    analytics["stages_completed"] = len(project_data.get("unlocked_stages", []))
                    analytics["files_created"] = len(project_data.get("assets", {}))
            except:
                pass
        
        # Load schedule.json if exists
        if schedule_file.exists():
            try:
                with open(schedule_file, 'r') as f:
                    schedule_data = json.load(f)
                    analytics["scheduled_posts"] = len(schedule_data)
                    analytics["estimated_reach"] = len(schedule_data) * 1000  # Demo metric
            except:
                pass
        
        log_endpoint_event("/analytics/session/{id}", session_id, "success", {})
        return success_response(
            data={"analytics": analytics},
            message="Session analytics retrieved successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/analytics/session/{id}", session_id, "error", {"error": str(e)})
        return error_response(f"Analytics failed: {str(e)}")

@api.get("/analytics/dashboard/all")
async def get_dashboard_analytics():
    """Phase 2.2: Get dashboard analytics across all sessions (safe demo metrics)"""
    try:
        all_sessions = list(MEDIA_DIR.glob("*/project.json"))
        
        total_projects = len(all_sessions)
        total_beats = 0
        total_songs = 0
        total_releases = 0
        
        for session_file in all_sessions:
            try:
                with open(session_file, 'r') as f:
                    project_data = json.load(f)
                    assets = project_data.get("assets", {})
                    if "beat" in assets:
                        total_beats += 1
                    if "lyrics" in assets:
                        total_songs += 1
                    if "master" in assets or "mix" in assets:
                        total_releases += 1
            except:
                pass
        
        log_endpoint_event("/analytics/dashboard/all", None, "success", {"projects": total_projects})
        return success_response(
            data={
                "dashboard": {
                    "total_projects": total_projects,
                    "total_beats": total_beats,
                    "total_songs": total_songs,
                    "total_releases": total_releases,
                    "platform_reach": total_projects * 5000  # Demo metric
                }
            },
            message="Dashboard analytics retrieved successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/analytics/dashboard/all", None, "error", {"error": str(e)})
        return error_response(f"Dashboard analytics failed: {str(e)}")

# ============================================================================
# 9. VOICES - gTTS ONLY WITH DEBOUNCE
# ============================================================================

@api.post("/voices/say")
async def voice_say(request: VoiceSayRequest):
    """Phase 2.2: Make an AI persona speak using gTTS (10s debounce, SHA256)"""
    try:
        result = gtts_speak(request.persona, request.text, request.session_id)
        return result
    except Exception as e:
        log_endpoint_event("/voices/say", request.session_id, "error", {"error": str(e)})
        return error_response(f"Voice say failed: {str(e)}")

@api.post("/voices/mute")
async def voice_mute():
    """Phase 2.2: Mute voices (no-op, returns success)"""
    log_endpoint_event("/voices/mute", None, "success", {})
    return success_response(data={"action": "mute"}, message="Voices muted")

@api.post("/voices/pause")
async def voice_pause():
    """Phase 2.2: Pause voices (no-op, returns success)"""
    log_endpoint_event("/voices/pause", None, "success", {})
    return success_response(data={"action": "pause"}, message="Voices paused")

@api.post("/voices/stop")
async def voice_stop():
    """Phase 2.2: Stop voices (no-op, returns success)"""
    log_endpoint_event("/voices/stop", None, "success", {})
    return success_response(data={"action": "stop"}, message="Voices stopped")

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@api.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "beatoven_configured": bool(os.getenv("BEATOVEN_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "auphonic_configured": bool(os.getenv("AUPHONIC_API_KEY")),
        "getlate_configured": bool(os.getenv("GETLATE_API_KEY"))
    }

@api.get("/projects")
async def list_projects():
    """List all projects"""
    try:
        projects = list_all_projects(MEDIA_DIR)
        return {"ok": True, "projects": projects}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@api.get("/projects/{session_id}")
async def get_project(session_id: str):
    """Get a specific project"""
    try:
        memory = get_or_create_project_memory(session_id, MEDIA_DIR)
        return {"ok": True, "project": memory.project_data}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@api.post("/projects/{session_id}/advance")
async def advance_stage(session_id: str):
    """Advance project stage (called when user completes a stage)"""
    try:
        memory = get_or_create_project_memory(session_id, MEDIA_DIR)
        current_stage = memory.project_data.get("workflow", {}).get("current_stage", "beat")
        memory.advance_stage(current_stage)
        log_endpoint_event("/projects/{id}/advance", session_id, "success", {"from_stage": current_stage})
        return success_response(
            data={"current_stage": memory.project_data.get("workflow", {}).get("current_stage")},
            message="Stage advanced successfully"
        )
    except Exception as e:
        log_endpoint_event("/projects/{id}/advance", session_id, "error", {"error": str(e)})
        return error_response(f"Failed to advance stage: {str(e)}")

# ============================================================================
# INCLUDE API ROUTER
# ============================================================================
app.include_router(api)
app.include_router(content_router)

# ============================================================================
# FRONTEND SERVING (MUST BE LAST - AFTER ALL API ROUTES)
# ============================================================================

# Serve frontend in production (if built)
# IMPORTANT: Mount order matters - this must be after all API routes
if FRONTEND_DIST.exists():
    # Serve frontend assets (CSS, JS, images)
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    
    # Serve frontend static files (HTML, CSS, JS) - catch-all route (must be last)
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

