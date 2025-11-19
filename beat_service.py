"""
Beat Service - Business logic for beat generation
"""
import os
import uuid
import shutil
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from pydub import AudioSegment

from project_memory import get_or_create_project_memory
from backend.orchestrator import ProjectOrchestrator
from backend.utils.responses import success_response, error_response
from utils.helpers import get_session_media_path, log_endpoint_event

logger = logging.getLogger(__name__)

# Constants
MEDIA_DIR = Path("./media")
ASSETS_DIR = Path("./assets")


class BeatService:
    """Service class for beat generation business logic"""
    
    def __init__(self):
        self.api_key = os.getenv("BEATOVEN_API_KEY")
    
    async def create_beat_track(
        self,
        user_id: str,
        session_id: str,
        prompt: Optional[str] = None,
        mood: str = "energetic",
        genre: str = "hip-hop",
        bpm: Optional[int] = None,
        duration_sec: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a beat track using Beatoven API with fallback logic.
        
        Returns:
            Dict with beat_url, status, provider, progress, and session_id
        """
        session_path = get_session_media_path(session_id, user_id)
        
        # Log request
        if duration_sec is not None:
            logger.info(f"🎵 Beat creation request: prompt={prompt[:50] if prompt else ''}..., mood={mood}, genre={genre}, bpm={bpm or 'AI-determined'}, duration={duration_sec}s, session={session_id}")
        else:
            logger.info(f"🎵 Beat creation request: prompt={prompt[:50] if prompt else ''}..., mood={mood}, genre={genre}, bpm={bpm or 'AI-determined'}, duration=AI-determined, session={session_id}")
        
        # Build prompt text
        if prompt:
            prompt_text = prompt
            if mood and mood != "energetic":
                prompt_text += f", {mood} mood"
            if genre and genre != "hip-hop":
                prompt_text += f", {genre} style"
        else:
            prompt_text = f"{mood} {genre} instrumental track"
        
        # Add duration to prompt if provided
        if duration_sec is not None:
            prompt_text = f"{duration_sec} seconds {prompt_text}"
        
        # Try Beatoven API first if key available
        if self.api_key:
            try:
                # 1. Call Beatoven compose API
                task_id = await self._call_beatoven_compose(prompt_text)
                
                # 2. Poll for status and finalize
                current_user = {"id": user_id}  # For compatibility with existing code
                result = await self._poll_beatoven_status(
                    task_id=task_id,
                    session_path=session_path,
                    current_user=current_user,
                    session_id=session_id,
                    mood=mood,
                    genre=genre,
                    bpm=bpm
                )
                
                if result:
                    return result
            except httpx.RequestError as e:
                logger.warning(f"Beatoven API request failed: {e} - falling back to demo beat")
            except Exception as e:
                logger.warning(f"Beatoven API failed: {e} - falling back to demo beat")
        
        # 3. FALLBACK: Always return a beat (ALWAYS succeeds)
        return await self._handle_fallback_beat(
            session_path=session_path,
            user_id=user_id,
            session_id=session_id,
            bpm=bpm,
            mood=mood,
            genre=genre,
            duration_sec=duration_sec
        )
    
    async def _call_beatoven_compose(self, prompt_text: str) -> str:
        """
        Call Beatoven compose API to initiate beat generation.
        
        Args:
            prompt_text: The prompt text for beat generation
            
        Returns:
            task_id: The task ID returned by the API
            
        Raises:
            Exception: If the API call fails or returns an error
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {"prompt": {"text": prompt_text}, "format": "mp3", "looping": False}
        
        logger.info(f"🎵 Beatoven job started: {prompt_text}")
        
        compose_url = "https://public-api.beatoven.ai/api/v1/tracks/compose"
        async with httpx.AsyncClient() as client:
            compose_res = await client.post(compose_url, headers=headers, json=payload, timeout=30)
        
        # Handle HTTP errors gracefully
        if compose_res.status_code == 422:
            error_detail = compose_res.text
            logger.warning(f"Beatoven API returned 422 Unprocessable Content: {error_detail}")
            raise Exception(f"Beatoven API validation error: {error_detail}")
        elif compose_res.status_code == 401:
            logger.warning(f"Beatoven API returned 401 Unauthorized - invalid API key")
            raise Exception("Beatoven API authentication failed")
        elif not compose_res.is_success:
            error_detail = compose_res.text
            logger.warning(f"Beatoven API returned {compose_res.status_code}: {error_detail}")
            raise Exception(f"Beatoven API error {compose_res.status_code}: {error_detail}")
        
        compose_data = compose_res.json()
        task_id = compose_data.get("task_id")
        
        if not task_id:
            raise Exception("Beatoven: no task_id returned")
        
        logger.info(f"✅ Beatoven task started: {task_id}")
        return task_id
    
    async def _poll_beatoven_status(
        self,
        task_id: str,
        session_path: Path,
        current_user: Dict[str, str],
        session_id: str,
        mood: str,
        genre: str,
        bpm: Optional[int]
    ) -> Dict[str, Any]:
        """
        Poll Beatoven API for task completion and finalize the beat.
        
        Args:
            task_id: The task ID from the compose API call
            session_path: Path to the session media directory
            current_user: User dictionary with user information
            session_id: Session ID
            mood: Mood of the beat
            genre: Genre of the beat
            bpm: Optional BPM value
            
        Returns:
            Dict with beat_url, status, provider, progress, and session_id
            
        Raises:
            Exception: If polling fails, times out, or encounters an error
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        user_id = current_user.get("id", "")
        
        # Poll for completion (up to 3 minutes)
        async with httpx.AsyncClient() as client:
            for attempt in range(60):
                await asyncio.sleep(3)
                status_url = f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}"
                status_res = await client.get(status_url, headers=headers, timeout=30)
                
                if not status_res.is_success:
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
                    audio_data = await client.get(audio_url, timeout=60)
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
                    memory = await get_or_create_project_memory(session_id, MEDIA_DIR)
                    await memory.update_metadata(tempo=extracted_bpm, mood=mood, genre=genre)
                    await memory.add_asset("beat", f"/media/{user_id}/{session_id}/beat.mp3", {"bpm": extracted_bpm, "mood": mood, "metadata": extracted_metadata})
                    await memory.advance_stage("beat", "lyrics")
                    
                    # Prepare beat_url and beat_meta for orchestrator
                    beat_url = f"/media/{user_id}/{session_id}/beat.mp3"
                    beat_meta = {
                        "bpm": extracted_bpm,
                        "mood": mood,
                        "genre": genre,
                        "provider": "beatoven",
                        **extracted_metadata
                    }
                    
                    # Auto-save to orchestrator
                    orchestrator = ProjectOrchestrator(user_id, session_id)
                    orchestrator.update_stage("beat", {
                        "url": beat_url,
                        "meta": beat_meta,
                        "completed": True
                    })
                    
                    log_endpoint_event("/beats/create", session_id, "success", {"source": "beatoven", "mood": mood})
                    
                    return {
                        "session_id": session_id,
                        "beat_url": beat_url,
                        "url": beat_url,
                        "status": "ready",
                        "provider": "beatoven",
                        "progress": 100
                    }
                
                elif status in ("composing", "running", "queued"):
                    logger.info(f"⏳ Beatoven status: {status} ({attempt+1}/60)")
                    continue
                else:
                    raise Exception(f"Unexpected Beatoven status: {status}")
        
        raise Exception("Beatoven generation timed out (3 minutes)")
    
    async def _handle_fallback_beat(
        self,
        session_path: Path,
        user_id: str,
        session_id: str,
        bpm: Optional[int],
        mood: str,
        genre: str,
        duration_sec: Optional[int]
    ) -> Dict[str, Any]:
        """Create fallback beat (demo or silent)"""
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
            memory = await get_or_create_project_memory(session_id, MEDIA_DIR)
            demo_metadata = {"duration": 60, "bpm": bpm or 120, "key": "C"}
            await memory.update_metadata(tempo=bpm or 120, mood=mood, genre=genre)
            await memory.add_asset("beat", f"/media/{user_id}/{session_id}/beat.mp3", {"bpm": bpm or 120, "mood": mood, "source": "demo", "metadata": demo_metadata})
            await memory.advance_stage("beat", "lyrics")
            
            # Prepare beat_url and beat_meta for orchestrator
            beat_url = f"/media/{user_id}/{session_id}/beat.mp3"
            beat_meta = {
                "bpm": bpm or 120,
                "mood": mood,
                "genre": genre,
                "provider": "demo",
                **demo_metadata
            }
            
            # Auto-save to orchestrator
            orchestrator = ProjectOrchestrator(user_id, session_id)
            orchestrator.update_stage("beat", {
                "url": beat_url,
                "meta": beat_meta,
                "completed": True
            })
            
            log_endpoint_event("/beats/create", session_id, "success", {"source": "demo", "mood": mood})
            
            return {
                "session_id": session_id,
                "url": beat_url,
                "beat_url": beat_url,
                "status": "ready",
                "provider": "demo",
                "progress": 100
            }
        
        except Exception as e:
            # Ultimate fallback - create silent audio in session directory
            logger.error(f"Fallback beat creation failed: {e} - creating silent audio in session")
            try:
                output_file = session_path / "beat.mp3"
                silent_audio = AudioSegment.silent(duration=(duration_sec or 60) * 1000)
                silent_audio.export(str(output_file), format="mp3")
                
                memory = await get_or_create_project_memory(session_id, MEDIA_DIR)
                silent_metadata = {"duration": duration_sec or 60, "bpm": bpm or 120, "key": "C"}
                await memory.update_metadata(tempo=bpm or 120, mood=mood, genre=genre)
                await memory.add_asset("beat", f"/media/{user_id}/{session_id}/beat.mp3", {"bpm": bpm or 120, "mood": mood, "source": "silent_fallback", "metadata": silent_metadata})
                
                # Auto-save to orchestrator
                try:
                    orchestrator = ProjectOrchestrator(user_id, session_id)
                    orchestrator.update_stage("beat", {
                        "url": f"/media/{user_id}/{session_id}/beat.mp3",
                        "meta": {
                            "bpm": bpm or 120,
                            "mood": mood,
                            "genre": genre,
                            "provider": "silent_fallback",
                            **silent_metadata
                        },
                        "completed": True
                    })
                except Exception as e:
                    logger.warning(f"Failed to auto-save beat stage: {e}")
                
                log_endpoint_event("/beats/create", session_id, "success", {"source": "silent_fallback", "mood": mood})
                
                return {
                    "session_id": session_id,
                    "url": f"/media/{user_id}/{session_id}/beat.mp3",
                    "beat_url": f"/media/{user_id}/{session_id}/beat.mp3",
                    "status": "ready",
                    "provider": "silent_fallback",
                    "progress": 100
                }
            except Exception as final_error:
                logger.error(f"Complete beat generation failure: {final_error}")
                raise Exception(f"Beat generation failed: {final_error}")
    
    async def get_credits(self) -> Dict[str, Any]:
        """
        Get remaining credits from Beatoven API.
        
        Returns:
            Dict with credits count
        """
        api_key = os.getenv("BEATOVEN_API_KEY") or os.getenv("BEATOVEN_KEY")
        
        if not api_key:
            logger.warning("Beatoven API key not set – returning default credits")
            log_endpoint_event("/beats/credits", None, "success", {"credits": 10, "source": "default"})
            return {"credits": 10, "source": "default"}
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            credits_url = "https://public-api.beatoven.ai/api/v1/usage"
            try:
                import requests
                credits_res = requests.get(credits_url, headers=headers, timeout=10)
                if credits_res.ok:
                    credits_data = credits_res.json()
                    credits = credits_data.get("credits", credits_data.get("remaining", 10))
                    log_endpoint_event("/beats/credits", None, "success", {"credits": credits, "source": "beatoven"})
                    return {"credits": credits, "source": "beatoven"}
            except:
                pass
            
            # Fallback: return default credits
            logger.warning("Beatoven credits API not available – using fallback default")
            log_endpoint_event("/beats/credits", None, "success", {"credits": 10, "source": "fallback"})
            return {"credits": 10, "source": "fallback"}
        except Exception as e:
            logger.warning(f"Failed to get Beatoven credits: {e}")
            log_endpoint_event("/beats/credits", None, "error", {"error": str(e)})
            raise Exception(f"Failed to fetch beat credits: {str(e)}")
    
    async def get_beat_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a beat generation job.
        
        Returns:
            Dict with job status or None if not found
        """
        # This is a stub implementation - would need actual job tracking
        # For now, return None to indicate job not found
        return None

