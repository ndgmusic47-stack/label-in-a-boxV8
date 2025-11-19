"""
Beat Router - API endpoints for beat generation
"""
import uuid
from fastapi import APIRouter, Body, Depends
from typing import Optional
from pydantic import BaseModel, Field

from auth import get_current_user
from services.beat_service import BeatService
from backend.utils.responses import success_response, error_response
from utils.helpers import log_endpoint_event

# Create router
beat_router = APIRouter(prefix="/api/beats", tags=["beats"])

# Request models
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

# Service instance
beat_service = BeatService()


@beat_router.post("/create")
async def create_beat(
    request: Optional[BeatRequest] = Body(default=None),
    current_user: dict = Depends(get_current_user)
):
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
    
    try:
        result = await beat_service.create_beat_track(
            user_id=current_user["user_id"],
            session_id=session_id,
            prompt=prompt,
            mood=mood,
            genre=genre,
            bpm=bpm,
            duration_sec=duration_sec if duration_provided else None
        )
        
        return success_response(
            data=result,
            message="Beat generation started"
        )
    except Exception as e:
        log_endpoint_event("/beats/create", session_id, "error", {"error": str(e)})
        return error_response(
            f"Beat generation failed: {str(e)}",
            status_code=500,
            data={"session_id": session_id}
        )


@beat_router.get("/credits")
async def get_beat_credits():
    """Get remaining credits from Beatoven API"""
    try:
        result = await beat_service.get_credits()
        return success_response(
            data={"credits": result["credits"]},
            message="Credits retrieved" + (f" ({result['source']})" if result.get("source") else "")
        )
    except Exception as e:
        log_endpoint_event("/beats/credits", None, "error", {"error": str(e)})
        return error_response(
            str(e),
            status_code=500,
            data={}
        )


@beat_router.get("/status/{job_id}")
async def get_beat_status(job_id: str):
    """Get the status of a beat generation job"""
    job = await beat_service.get_beat_status(job_id)
    
    if job is None:
        return error_response(
            f"Beat job {job_id} not found",
            status_code=404,
            data={}
        )
    
    # If job exists, return status
    if job.get("status") in ["ready", "error"]:
        return success_response(
            data={
                "job_id": job_id,
                "status": job.get("status"),
                "progress": job.get("progress", 0),
                "beat_url": job.get("beat_url"),
                "message": job.get("message")
            },
            message="Beat job status updated"
        )
    
    # Poll for updates (placeholder)
    return success_response(
        data={
            "job_id": job_id,
            "status": job.get("status", "processing"),
            "progress": job.get("progress", 0),
            "beat_url": job.get("beat_url")
        },
        message="Beat job in progress"
    )

