"""
Lyrics Router - API endpoints for lyrics generation
"""
import uuid
from fastapi import APIRouter, File, UploadFile, Form, Body, Depends
from typing import Optional, List
from pydantic import BaseModel, Field
from pathlib import Path

from auth import get_current_user
from services.lyrics_service import LyricsService
from backend.utils.responses import success_response, error_response
from utils.helpers import log_endpoint_event

# Import gtts_speak - will be imported at runtime to avoid circular import
# We'll handle this in the endpoint by importing it there
gtts_speak = None

# Create router
lyrics_router = APIRouter(prefix="/api", tags=["lyrics"])

# Request models
class SongRequest(BaseModel):
    genre: str = Field(default="hip hop")
    mood: str = Field(default="energetic")
    theme: Optional[str] = None
    session_id: Optional[str] = Field(None)
    beat_context: Optional[dict] = Field(None, description="Beat metadata (tempo/key/energy)")

class FreeLyricsRequest(BaseModel):
    theme: str = Field(..., description="Theme for the lyrics")

class LyricRefineRequest(BaseModel):
    lyrics: str = Field(..., description="Full current lyrics as text")
    instruction: str = Field(..., description="User instruction for refinement")
    bpm: Optional[int] = Field(default=None, description="Beats per minute (optional)")
    history: Optional[List[dict]] = Field(default=[], description="V18.1: Recent conversation history (last 3 interactions)")
    structured_lyrics: Optional[dict] = Field(default=None, description="V18.1: Structured lyrics object with sections")
    rhythm_map: Optional[dict] = Field(default=None, description="V18.1: Rhythm approximation map per section")

# Service instance
lyrics_service = LyricsService()


@lyrics_router.post("/songs/write")
async def write_song(
    request: SongRequest,
    current_user: dict = Depends(get_current_user)
):
    """Phase 2.2: Generate song lyrics using OpenAI with fallback"""
    session_id = request.session_id if request.session_id else str(uuid.uuid4())
    
    try:
        result = await lyrics_service.write_song(
            user_id=current_user["user_id"],
            session_id=session_id,
            genre=request.genre,
            mood=request.mood,
            theme=request.theme,
            beat_context=request.beat_context
        )
        
        # Generate voice MP3 for lyrics using gTTS (first 200 chars to avoid too long)
        voice_url = None
        try:
            # Import at runtime to avoid circular import
            from main import gtts_speak
            
            try:
                # Parse lyrics to get first verse
                lyrics_text = result.get("lyrics", "")
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
                
                # Use first verse or first 200 chars for voice generation
                voice_text = parsed_lyrics.get("verse", "").split('\n')[0] if parsed_lyrics.get("verse") else (lyrics_text.split('\n')[0] if lyrics_text else "Here are your lyrics")
                if len(voice_text) > 200:
                    voice_text = voice_text[:200] + "..."
                
                # Generate voice using default persona "nova"
                voice_result = gtts_speak("nova", voice_text, session_id, current_user["user_id"])
                if isinstance(voice_result, dict) and voice_result.get("ok"):
                    voice_url = voice_result.get("data", {}).get("url")
                    import logging
                    logging.getLogger(__name__).info(f"Generated voice for lyrics: {voice_url}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Voice generation for lyrics failed: {e}")
        
        log_endpoint_event("/songs/write", session_id, "success", {"voice_generated": voice_url is not None})
        return success_response(
            data=result,
            message="Lyrics generated"
        )
    except Exception as e:
        log_endpoint_event("/songs/write", session_id, "error", {"error": str(e)})
        return error_response(
            "Failed to generate lyrics",
            status_code=500,
            data={"session_id": session_id}
        )


@lyrics_router.post("/lyrics/from_beat")
async def generate_lyrics_from_beat(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """V17: Generate NP22-style lyrics from uploaded beat file"""
    session_id = session_id if session_id else str(uuid.uuid4())
    session_path = Path("./media") / current_user["user_id"] / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save uploaded file temporarily
        temp_file = session_path / f"temp_beat_{uuid.uuid4().hex[:8]}.mp3"
        content = await file.read()
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        result = await lyrics_service.generate_lyrics_from_beat(
            user_id=current_user["user_id"],
            session_id=session_id,
            beat_file_path=temp_file
        )
        
        # Clean up temp file
        try:
            temp_file.unlink()
        except:
            pass
        
        return success_response(
            data=result,
            message="Lyrics generated from beat"
        )
    except Exception as e:
        log_endpoint_event("/lyrics/from_beat", session_id, "error", {"error": str(e)})
        return error_response(
            "Failed to generate lyrics from beat",
            status_code=500,
            data={"session_id": session_id}
        )


@lyrics_router.post("/lyrics/free")
async def generate_free_lyrics(request: FreeLyricsRequest):
    """V17: Generate NP22-style lyrics from theme only"""
    try:
        result = await lyrics_service.generate_free_lyrics(theme=request.theme)
        return success_response(
            data=result,
            message="Lyrics generated"
        )
    except Exception as e:
        log_endpoint_event("/lyrics/free", None, "error", {"error": str(e)})
        return error_response(
            "Failed to generate lyrics",
            status_code=500,
            data={}
        )


@lyrics_router.post("/lyrics/refine")
async def refine_lyrics(request: LyricRefineRequest):
    """V18.1: Refine, rewrite, or extend lyrics based on user instructions with structured parsing and history"""
    try:
        result = await lyrics_service.refine_lyrics(
            lyrics=request.lyrics,
            instruction=request.instruction,
            bpm=request.bpm,
            history=request.history,
            structured_lyrics=request.structured_lyrics,
            rhythm_map=request.rhythm_map
        )
        return success_response(
            data=result,
            message="Lyrics refined"
        )
    except Exception as e:
        log_endpoint_event("/lyrics/refine", None, "error", {"error": str(e)})
        return error_response(
            "Failed to refine lyrics",
            status_code=500,
            data={}
        )

