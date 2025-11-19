"""
Release Router - API endpoints for release pack generation
"""
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from services.release_service import ReleaseService
from backend.utils.responses import success_response, error_response
from utils.shared_utils import get_session_media_path, log_endpoint_event, require_feature_pro
from database import get_db
from backend.orchestrator import ProjectOrchestrator

# Create router
release_router = APIRouter(prefix="/api/release", tags=["release"])

# Request models
class ReleaseCoverRequest(BaseModel):
    session_id: str
    track_title: str
    artist_name: str
    genre: str
    mood: str
    style: Optional[str] = Field(default="realistic", description="realistic / abstract / cinematic / illustrated / purple-gold aesthetic")

class ReleaseSelectCoverRequest(BaseModel):
    session_id: str
    cover_url: str

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

class ReleaseBuildRequest(BaseModel):
    session_id: str
    title: str
    artist: str
    cover_prompt: Optional[str] = None
    release_date: Optional[str] = None
    user_id: Optional[str] = None
    plan: Optional[str] = "free"
    trial_started_at: Optional[str] = None
    subscription_active: Optional[bool] = False

class ReleaseRequest(BaseModel):
    session_id: str
    title: Optional[str] = None
    artist: Optional[str] = None
    mixed_file: Optional[str] = None
    cover_file: Optional[str] = None
    metadata: Optional[dict] = None
    lyrics: Optional[str] = ""

class ReleaseFilesRequest(BaseModel):
    session_id: str

# Service instance
release_service = ReleaseService()

# Constants
MEDIA_DIR = Path("./media")


@release_router.post("/cover")
async def generate_release_cover(
    request: ReleaseCoverRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI cover art using OpenAI (3 images, 3000x3000, 1500x1500, 1080x1920)"""
    try:
        result = await release_service.generate_cover_art(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            track_title=request.track_title,
            artist_name=request.artist_name,
            genre=request.genre,
            mood=request.mood,
            style=request.style
        )
        
        if not result.get("success"):
            return error_response(result.get("error", "Cover art generation failed"))
        
        log_endpoint_event("/release/cover", request.session_id, "success", {"count": len(result.get("images", []))})
        return success_response(
            data={
                "project_id": request.session_id,
                "stage": "release",
                "images": result.get("images", []),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            message="Cover art generated successfully"
        )
    except Exception as e:
        log_endpoint_event("/release/cover", request.session_id, "error", {"error": str(e)})
        return error_response(f"Cover art generation failed: {str(e)}")


@release_router.post("/select-cover")
async def select_release_cover(
    request: ReleaseSelectCoverRequest,
    current_user: dict = Depends(get_current_user)
):
    """Save selected cover art to final versions (3000, 1500, vertical) and update memory"""
    try:
        result = await release_service.select_cover_art(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            cover_url=request.cover_url
        )
        
        if not result.get("success"):
            return error_response(result.get("error", "Failed to select cover art"))
        
        log_endpoint_event("/release/select-cover", request.session_id, "success", {})
        return success_response(
            data={
                "project_id": request.session_id,
                "stage": "release",
                "final_cover": result.get("final_cover"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            message="Cover art selected successfully"
        )
    except Exception as e:
        log_endpoint_event("/release/select-cover", request.session_id, "error", {"error": str(e)})
        return error_response(f"Failed to select cover art: {str(e)}")


@release_router.post("/copy")
async def generate_release_copy(
    request: ReleaseCopyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate release copy: release_description.txt, press_pitch.txt, tagline.txt"""
    try:
        result = await release_service.generate_release_copy(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            track_title=request.track_title,
            artist_name=request.artist_name,
            genre=request.genre,
            mood=request.mood,
            lyrics=request.lyrics or ""
        )
        
        if not result.get("success"):
            return error_response(result.get("error", "Release copy generation failed"))
        
        log_endpoint_event("/release/copy", request.session_id, "success", {})
        return success_response(
            data={
                "description_url": result.get("description_url"),
                "pitch_url": result.get("pitch_url"),
                "tagline_url": result.get("tagline_url")
            },
            message="Release copy generated successfully"
        )
    except Exception as e:
        log_endpoint_event("/release/copy", request.session_id, "error", {"error": str(e)})
        return error_response(f"Release copy generation failed: {str(e)}")


@release_router.post("/lyrics")
async def generate_lyrics_pdf(
    request: ReleaseRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate lyrics.pdf if lyrics exist"""
    try:
        result = await release_service.generate_lyrics_pdf(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            title=request.title,
            artist=request.artist,
            lyrics=request.lyrics
        )
        
        if not result.get("success"):
            return error_response(result.get("error", "Lyrics PDF generation failed"))
        
        if result.get("skipped"):
            log_endpoint_event("/release/lyrics", request.session_id, "success", {"skipped": True})
            return success_response(
                data={"skipped": True, "message": "No lyrics found"},
                message="No lyrics to generate PDF for"
            )
        
        log_endpoint_event("/release/lyrics", request.session_id, "success", {})
        return success_response(
            data={"pdf_url": result.get("pdf_url")},
            message="Lyrics PDF generated successfully"
        )
    except Exception as e:
        log_endpoint_event("/release/lyrics", request.session_id, "error", {"error": str(e)})
        return error_response(f"Lyrics PDF generation failed: {str(e)}")


@release_router.post("/metadata")
async def generate_release_metadata(
    request: ReleaseMetadataRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate metadata.json with track info"""
    try:
        result = await release_service.generate_metadata(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            user_plan=current_user.get("plan", "free"),
            track_title=request.track_title,
            artist_name=request.artist_name,
            genre=request.genre,
            mood=request.mood,
            explicit=request.explicit,
            release_date=request.release_date
        )
        
        if not result.get("success"):
            return error_response(
                result.get("error", "Metadata generation failed"),
                status_code=result.get("status_code", 500)
            )
        
        log_endpoint_event("/release/metadata", request.session_id, "success", {})
        return success_response(
            data={"metadata_url": result.get("metadata_url")},
            message="Metadata generated successfully"
        )
    except Exception as e:
        log_endpoint_event("/release/metadata", request.session_id, "error", {"error": str(e)})
        return error_response(f"Metadata generation failed: {str(e)}")


@release_router.post("/build")
async def build_release_pack(request: ReleaseBuildRequest):
    """
    PHASE 5: Build complete release pack with standardized structure.
    Validates inputs and generates cover, metadata, and copies audio.
    """
    # Access control check
    from backend.auth.user import User
    from backend.auth.billing import user_can_use_feature
    
    if not request.user_id:
        return error_response(
            "PAYWALL",
            402,
            "This action requires an active subscription or trial."
        )
    
    user = User(
        user_id=request.user_id,
        plan=request.plan or "free",
        trial_started_at=request.trial_started_at,
        subscription_active=request.subscription_active or False
    )
    
    if not user_can_use_feature(user, "release"):
        return error_response(
            "PAYWALL",
            402,
            "This action requires an active subscription or trial."
        )
    
    try:
        # Validate required fields
        if not request.title or not request.title.strip():
            log_endpoint_event("/release/build", request.session_id, "error", {"error": "MISSING_FIELD", "field": "title"})
            return error_response("MISSING_FIELD", 400, "Missing required field: title", data={"field": "title"})
        
        if not request.artist or not request.artist.strip():
            log_endpoint_event("/release/build", request.session_id, "error", {"error": "MISSING_FIELD", "field": "artist"})
            return error_response("MISSING_FIELD", 400, "Missing required field: artist", data={"field": "artist"})
        
        if not request.session_id or not request.session_id.strip():
            log_endpoint_event("/release/build", request.session_id, "error", {"error": "MISSING_FIELD", "field": "session_id"})
            return error_response("MISSING_FIELD", 400, "Missing required field: session_id", data={"field": "session_id"})
        
        # Validate cover prompt exists (required)
        if not request.cover_prompt or not request.cover_prompt.strip():
            log_endpoint_event("/release/build", request.session_id, "error", {"error": "MISSING_FIELD", "field": "cover_prompt"})
            return error_response("MISSING_FIELD", 400, "Missing required field: cover_prompt", data={"field": "cover_prompt"})
        
        # Find mixed file
        session_path = get_session_media_path(request.session_id, request.user_id)
        mixed_file_path = None
        
        # Try to find mixed/mastered file
        for filename in ["mix/mixed_mastered.wav", "mix.wav", "master.wav", "release/audio/mixed_mastered.wav"]:
            candidate_path = session_path / filename
            if candidate_path.exists():
                mixed_file_path = candidate_path
                break
        
        if not mixed_file_path or not mixed_file_path.exists():
            log_endpoint_event("/release/build", request.session_id, "error", {"error": "MISSING_FIELD", "field": "mixed_file"})
            return error_response("MISSING_FIELD", 400, "Missing required field: mixed_file", data={"field": "mixed_file"})
        
        # Build release pack
        result = release_service.build_release_pack(
            session_id=request.session_id,
            title=request.title,
            artist=request.artist,
            mixed_file_path=mixed_file_path,
            cover_prompt=request.cover_prompt,
            release_date=request.release_date,
            user_id=request.user_id
        )
        
        if not result.get("ok"):
            error_msg = result.get("error", "Unknown error")
            log_endpoint_event("/release/build", request.session_id, "error", {"error": error_msg})
            return error_response(error_msg, 400, error_msg, data=result.get("data", {}))
        
        # Phase 6: Auto-save to orchestrator
        orchestrator = ProjectOrchestrator(request.user_id, request.session_id)
        release_data = result.get("data", {})
        cover_url = release_data.get("cover_url")
        song_url = release_data.get("song_url")
        metadata_url = release_data.get("metadata_url")
        orchestrator.update_stage("release", {
            "cover_url": cover_url,
            "song_url": song_url,
            "metadata_url": metadata_url,
            "completed": True
        })
        
        log_endpoint_event("/release/build", request.session_id, "success", {})
        return success_response(
            data=result.get("data", {}),
            message=result.get("message", "Release pack successfully created.")
        )
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Release build endpoint failed: {e}", exc_info=True)
        log_endpoint_event("/release/build", request.session_id if 'request' in locals() else "unknown", "error", {"error": str(e)})
        return error_response("UNEXPECTED_ERROR", 500, f"Release build failed: {str(e)}")


@release_router.get("/files")
async def list_release_files(
    session_id: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """List all release files dynamically"""
    try:
        result = await release_service.list_release_files(
            session_id=session_id,
            user_id=current_user["user_id"]
        )
        
        if not result.get("success"):
            return error_response(result.get("error", "Failed to list release files"))
        
        log_endpoint_event("/release/files", session_id, "success", {"count": len(result.get("files", []))})
        return success_response(
            data={"files": result.get("files", [])},
            message=f"Found {len(result.get('files', []))} release files"
        )
    except Exception as e:
        log_endpoint_event("/release/files", session_id, "error", {"error": str(e)})
        return error_response(f"Failed to list release files: {str(e)}")


@release_router.get("/pack")
async def get_release_pack(
    session_id: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Get complete release pack data: cover art, metadata, lyrics PDF, release copy, and audio"""
    try:
        result = await release_service.get_release_pack(
            session_id=session_id,
            user_id=current_user["user_id"]
        )
        
        if not result.get("success"):
            return error_response(result.get("error", "Failed to get release pack"))
        
        log_endpoint_event("/release/pack", session_id, "success", {})
        return success_response(
            data=result.get("data", {}),
            message="Release pack data retrieved successfully"
        )
    except Exception as e:
        log_endpoint_event("/release/pack", session_id, "error", {"error": str(e)})
        return error_response(f"Failed to get release pack: {str(e)}")


@release_router.post("/download-all")
async def download_all_release_files(
    request: ReleaseRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate ZIP of all release files (desktop only)"""
    # Phase 8A: Feature gate for full release pack download
    deny = await require_feature_pro(
        current_user,
        feature="release_pack",
        endpoint="/release/download-all",
        db=db,
    )
    if deny is not None:
        return deny
    
    try:
        result = await release_service.download_all_release_files(
            session_id=request.session_id,
            user_id=current_user["user_id"]
        )
        
        if not result.get("success"):
            return error_response(result.get("error", "ZIP generation failed"))
        
        log_endpoint_event("/release/download-all", request.session_id, "success", {})
        return success_response(
            data={"zip_url": result.get("zip_url")},
            message="Release pack ZIP generated successfully"
        )
    except Exception as e:
        log_endpoint_event("/release/download-all", request.session_id, "error", {"error": str(e)})
        return error_response(f"ZIP generation failed: {str(e)}")


@release_router.get("/status/{job_id}")
async def get_release_status(job_id: str):
    """Get the status of a release job"""
    try:
        result = await release_service.get_release_status(job_id)
        
        if not result.get("success"):
            return error_response(
                result.get("error", f"Release job {job_id} not found"),
                status_code=404,
                data={}
            )
        
        return success_response(
            data=result.get("data", {}),
            message="Release job status updated"
        )
    except Exception as e:
        return error_response(f"Failed to get release status: {str(e)}")

