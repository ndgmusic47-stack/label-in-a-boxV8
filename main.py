"""
Label-in-a-Box Phase 2 Backend - Production Demo
Clean backend using ONLY: Beatoven, OpenAI (text), Auphonic, GetLate, local services
"""

import os
import uuid
import json
import shutil
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging
import zipfile

from fastapi import FastAPI, APIRouter, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydub import AudioSegment
from PIL import Image
import requests
from datetime import timezone

# Import local services
from project_memory import get_or_create_project_memory, list_all_projects
from content import content_router
from auth import auth_router, get_current_user
from routers.billing_router import billing_router
from routers.beat_router import beat_router
from routers.lyrics_router import lyrics_router
from routers.media_router import media_router
from routers.release_router import release_router, ReleaseRequest
from routers.analytics_router import analytics_router
from routers.social_router import social_router
from utils.rate_limit import RateLimiterMiddleware
from utils.shared_utils import require_feature_pro, get_session_media_path, log_endpoint_event, gtts_speak
from backend.orchestrator import ProjectOrchestrator
from database import init_db, get_db
from sqlalchemy.ext.asyncio import AsyncSession

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

# Phase 1 normalized JSON response helpers - now from unified module
from backend.utils.responses import success_response, error_response

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(title="Label in a Box v4 - Phase 2.2")

# Phase 1: Required API keys for startup validation
REQUIRED_KEYS = [
    "OPENAI_API_KEY",
    "BEATOVEN_API_KEY",
    "BUFFER_TOKEN",
    "DISTROKID_KEY",
]

# CORS middleware (Phase 1 hardening)
allowed_origins = [
    "http://localhost:5173",
    "https://labelinabox.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Rate limiting middleware (Phase 1)
app.add_middleware(RateLimiterMiddleware, requests_per_minute=30)

# Enforce HTTPS in production (Render)
def _is_render_env() -> bool:
    return bool(os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RENDER_SERVICE_NAME"))

class EnforceHTTPSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if _is_render_env():
            proto = request.headers.get("x-forwarded-proto", "")
            if proto and proto.lower() != "https":
                return error_response("HTTPS required", status_code=403)
        return await call_next(request)

app.add_middleware(EnforceHTTPSMiddleware)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses: CSP, HSTS, X-Frame-Options, X-Content-Type-Options"""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Content-Security-Policy: Strict CSP to mitigate XSS risks
        # Allow self, inline scripts/styles (for frontend), and Beatoven API
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' https://public-api.beatoven.ai; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # Strict-Transport-Security: Enforce HTTPS for 1 year, include subdomains
        # Only set in production (Render environment) where HTTPS is guaranteed
        if _is_render_env():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # X-Frame-Options: Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        return response

app.add_middleware(SecurityHeadersMiddleware)

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
# STARTUP CHECKS - ENV KEYS (Phase 1)
# ============================================================================
@app.on_event("startup")
async def check_env_keys_on_startup():
    missing = []
    for env_key in ["OPENAI_API_KEY", "SUNO_API_KEY", "BUFFER_TOKEN", "DISTROKID_KEY"]:
        if not os.getenv(env_key):
            missing.append(env_key)
    if missing:
        logger.warning(f"Startup check: Missing environment variables: {', '.join(missing)}")
    else:
        logger.info("Startup check: All critical environment variables are set")

# Phase 1: Additional startup validation for required keys (non-fatal)
@app.on_event("startup")
async def validate_keys():
    missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
    if missing:
        logger.warning(f"⚠️ Missing API keys: {missing}")
    else:
        logger.info("🔐 All API keys loaded successfully")

# Initialize database on startup
@app.on_event("startup")
async def initialize_database():
    """Initialize the SQLite database and create all tables."""
    await init_db()
    logger.info("✅ Database initialized successfully")

# ============================================================================
# REQUEST MODELS
# ============================================================================
# Note: Request models have been moved to their respective router files:
# - BeatRequest -> routers/beat_router.py
# - SongRequest, FreeLyricsRequest, LyricRefineRequest -> routers/lyrics_router.py
# - CleanMixRequest -> models/mix.py
# - ReleaseRequest, ReleaseCoverRequest, etc. -> routers/release_router.py
# - SocialPostRequest -> routers/social_router.py

class VoiceSayRequest(BaseModel):
    persona: str = Field(..., description="echo, lyrica, nova, tone, aria, vee, or pulse")
    text: str
    session_id: Optional[str] = None

# ============================================================================
# VOICE DEBOUNCE SYSTEM (gTTS ONLY) - PHASE 2.2: 10s DEBOUNCE, SHA256 CACHE
# ============================================================================
# Moved to utils/shared_utils.py

# ============================================================================
# BEAT, LYRICS, UPLOAD, AND MIX ENDPOINTS MOVED TO ROUTERS
# See routers/beat_router.py, routers/lyrics_router.py, and routers/media_router.py
# ============================================================================

# ============================================================================
# 1.1. GET /credits - GET CREDITS (EXACT FORMAT: {"credits": <number>})
# ============================================================================

@api.get("/credits")
def get_credits():
    """Get remaining credits from Beatoven API - returns exactly {"credits": <number>}"""
    api_key = os.getenv("BEATOVEN_API_KEY") or os.getenv("BEATOVEN_KEY")
    
    if not api_key:
        # Return default credits if API key not configured
        logger.warning("Beatoven API key not set – returning default credits")
        log_endpoint_event("/credits", None, "success", {"credits": 10, "source": "default"})
        return JSONResponse(content={"credits": 10})
    
    try:
        # Try to get credits from Beatoven API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        credits_url = "https://public-api.beatoven.ai/api/v1/usage"
        try:
            credits_res = requests.get(credits_url, headers=headers, timeout=10)
            if credits_res.ok:
                credits_data = credits_res.json()
                credits = credits_data.get("credits", credits_data.get("remaining", 10))
                log_endpoint_event("/credits", None, "success", {"credits": credits, "source": "beatoven"})
                return JSONResponse(content={"credits": credits})
        except:
            pass
        
        # Fallback: return default credits
        logger.warning("Beatoven credits API not available – using fallback default")
        log_endpoint_event("/credits", None, "success", {"credits": 10, "source": "fallback"})
        return JSONResponse(content={"credits": 10})
    except Exception as e:
        logger.warning(f"Failed to get Beatoven credits: {e}")
        log_endpoint_event("/credits", None, "error", {"error": str(e)})
        return JSONResponse(status_code=500, content={"credits": 0})

# 1.1. GET /beats/credits - GET BEATOVEN CREDITS (LEGACY ENDPOINT)
# ============================================================================

@api.get("/beats/credits")
async def get_beat_credits():
    """Get remaining credits from Beatoven API"""
    api_key = os.getenv("BEATOVEN_API_KEY") or os.getenv("BEATOVEN_KEY")
    
    if not api_key:
        # Return default credits if API key not configured
        logger.warning("Beatoven API key not set – returning default credits")
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
        logger.warning("Beatoven credits API not available – using fallback default")
        log_endpoint_event("/beats/credits", None, "success", {"credits": 10, "source": "fallback"})
        return success_response(
            data={"credits": 10},
            message="Credits retrieved (fallback)"
        )
    except Exception as e:
        logger.warning(f"Failed to get Beatoven credits: {e}")
        log_endpoint_event("/beats/credits", None, "error", {"error": str(e)})
        return error_response(
            f"Failed to fetch beat credits: {str(e)}",
            status_code=500,
            data={}
        )

# ============================================================================
# 1.2. GET /beats/status/{job_id} - GET BEAT JOB STATUS
# ============================================================================

@api.get("/beats/status/{job_id}")
async def get_beat_status(job_id: str):
    """Get the status of a beat generation job"""
    # Check if job exists (placeholder - would need actual job tracking)
    # This is a stub implementation that matches the expected return patterns
    job = None  # Would be retrieved from job storage
    
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
    result = {
        "status": job.get("status", "processing"),
        "progress": job.get("progress", 0),
        "beat_url": job.get("beat_url"),
        "message": job.get("message")
    }
    
    return success_response(
        data={
            "job_id": job_id,
            "status": result.get("status"),
            "progress": result.get("progress", 0),
            "beat_url": result.get("beat_url"),
            "message": result.get("message")
        },
        message="Beat job status updated"
    )


# ============================================================================
# RELEASE MODULE - MOVED TO routers/release_router.py
# ============================================================================

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
# SOCIAL AND ANALYTICS MODULES - MOVED TO ROUTERS
# See routers/social_router.py and routers/analytics_router.py
# ============================================================================

# ============================================================================
# 9. VOICES - gTTS ONLY WITH DEBOUNCE
# ============================================================================

@api.post("/voices/say")
async def voice_say(request: VoiceSayRequest, current_user: dict = Depends(get_current_user)):
    """Phase 2.2: Make an AI persona speak using gTTS (10s debounce, SHA256)"""
    try:
        result = gtts_speak(request.persona, request.text, request.session_id, current_user["user_id"])
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
    return success_response(
        data={
            "status": "healthy",
            "beatoven_configured": bool(os.getenv("BEATOVEN_API_KEY")),
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "auphonic_configured": bool(os.getenv("AUPHONIC_API_KEY")),
            "getlate_configured": bool(os.getenv("GETLATE_API_KEY"))
        },
        message="OK"
    )

@api.get("/projects")
async def list_projects(current_user: dict = Depends(get_current_user)):
    """List all projects (requires authentication)"""
    try:
        user_id = current_user["user_id"]
        # List projects from user's directory
        user_media_dir = MEDIA_DIR / user_id
        projects = await list_all_projects(user_media_dir) if user_media_dir.exists() else []
        return success_response(data={"projects": projects}, message="Projects listed successfully")
    except Exception as e:
        return error_response(str(e), status_code=500)

@api.get("/projects/{session_id}")
async def get_project(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific project (requires authentication)"""
    try:
        user_id = current_user["user_id"]
        memory = await get_or_create_project_memory(session_id, MEDIA_DIR, user_id)
        return success_response(data={"project": memory.project_data}, message="Project retrieved successfully")
    except Exception as e:
        return error_response(str(e), status_code=500)

@api.post("/projects/{session_id}/advance")
async def advance_stage(session_id: str, current_user: dict = Depends(get_current_user)):
    """Advance project stage (called when user completes a stage) (requires authentication)"""
    try:
        user_id = current_user["user_id"]
        memory = await get_or_create_project_memory(session_id, MEDIA_DIR, user_id)
        current_stage = memory.project_data.get("workflow", {}).get("current_stage", "beat")
        await memory.advance_stage(current_stage)
        log_endpoint_event("/projects/{id}/advance", session_id, "success", {"from_stage": current_stage})
        return success_response(
            data={"current_stage": memory.project_data.get("workflow", {}).get("current_stage")},
            message="Stage advanced successfully"
        )
    except Exception as e:
        log_endpoint_event("/projects/{id}/advance", session_id, "error", {"error": str(e)})
        return error_response(f"Failed to advance stage: {str(e)}")

# ============================================================================
# PHASE 8.3: PROJECT SAVE/LOAD ROUTES
# ============================================================================

class ProjectSaveRequest(BaseModel):
    projectId: Optional[str] = None
    userId: str
    projectData: dict

class ProjectLoadRequest(BaseModel):
    projectId: str

@api.post("/projects/save")
async def save_project(request: ProjectSaveRequest, current_user: dict = Depends(get_current_user)):
    """Save project data to user's project folder"""
    try:
        user_id = current_user["user_id"]
        user_plan = current_user.get("plan", "free")
        
        # Generate projectId if not provided
        project_id = request.projectId or str(uuid.uuid4())
        
        # PHASE 8.4: Free tier limit enforcement - max 1 project
        if user_plan == "free":
            projects_dir = Path("./data/projects") / user_id
            if projects_dir.exists():
                existing_projects = list(projects_dir.glob("*.json"))
                # If this is a new project (not updating existing), check limit
                if not request.projectId and len(existing_projects) >= 1:
                    log_endpoint_event("/projects/save", project_id, "upgrade_required", {"user_id": user_id, "limit": "multi_project"})
                    return error_response("upgrade_required", status_code=403)
        
        # Create user's project directory
        projects_dir = Path("./data/projects") / user_id
        projects_dir.mkdir(parents=True, exist_ok=True)
        
        # Save project data
        project_file = projects_dir / f"{project_id}.json"
        
        # Extract name from projectData or use default
        project_name = request.projectData.get("metadata", {}).get("track_title") or "Untitled Project"
        
        project_save_data = {
            "projectId": project_id,
            "userId": user_id,
            "name": project_name,
            "projectData": request.projectData,
            "updatedAt": datetime.now().isoformat(),
            "createdAt": request.projectData.get("created_at", datetime.now().isoformat())
        }
        
        with open(project_file, 'w') as f:
            json.dump(project_save_data, f, indent=2)
        
        log_endpoint_event("/projects/save", project_id, "success", {"user_id": user_id})
        return success_response(
            data={"projectId": project_id, "name": project_name},
            message="Project saved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to save project: {e}")
        log_endpoint_event("/projects/save", request.projectId or "new", "error", {"error": str(e)})
        return error_response(f"Failed to save project: {str(e)}")

@api.get("/projects/list")
async def list_user_projects(current_user: dict = Depends(get_current_user)):
    """List all projects for the current user"""
    try:
        user_id = current_user["user_id"]
        projects_dir = Path("./data/projects") / user_id
        
        projects = []
        if projects_dir.exists():
            for project_file in projects_dir.glob("*.json"):
                try:
                    with open(project_file, 'r') as f:
                        data = json.load(f)
                        projects.append({
                            "projectId": data.get("projectId", project_file.stem),
                            "name": data.get("name", "Untitled Project"),
                            "updatedAt": data.get("updatedAt", "")
                        })
                except Exception as e:
                    logger.error(f"Error loading project {project_file}: {e}")
        
        # Sort by updatedAt descending
        projects.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
        
        log_endpoint_event("/projects/list", None, "success", {"user_id": user_id, "count": len(projects)})
        return success_response(data={"projects": projects}, message="Projects listed successfully")
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        log_endpoint_event("/projects/list", None, "error", {"error": str(e)})
        return error_response(f"Failed to list projects: {str(e)}")

@api.post("/projects/load")
async def load_project(request: ProjectLoadRequest, current_user: dict = Depends(get_current_user)):
    """Load a specific project"""
    try:
        user_id = current_user["user_id"]
        project_id = request.projectId
        
        projects_dir = Path("./data/projects") / user_id
        project_file = projects_dir / f"{project_id}.json"
        
        if not project_file.exists():
            return error_response("Project not found", status_code=404)
        
        with open(project_file, 'r') as f:
            data = json.load(f)
        
        log_endpoint_event("/projects/load", project_id, "success", {"user_id": user_id})
        return success_response(
            data={
                "projectData": data.get("projectData", {}),
                "projectId": data.get("projectId", project_id),
                "name": data.get("name", "Untitled Project")
            },
            message="Project loaded successfully"
        )
    except Exception as e:
        logger.error(f"Failed to load project: {e}")
        log_endpoint_event("/projects/load", request.projectId, "error", {"error": str(e)})
        return error_response(f"Failed to load project: {str(e)}")

# ============================================================================
# PHASE 6: PROJECT ORCHESTRATOR ENDPOINTS
# ============================================================================

class ProjectLoadRequestPhase6(BaseModel):
    session_id: str

@api.post("/project/load")
async def load_project(request: ProjectLoadRequestPhase6, current_user: dict = Depends(get_current_user)):
    orchestrator = ProjectOrchestrator(current_user["user_id"], request.session_id)
    state = await asyncio.to_thread(orchestrator.get_full_state)
    if not state:
        return error_response("PROJECT_NOT_FOUND", 404, "Project not found")
    return success_response(data=state)

@api.get("/project/state/{session_id}")
async def get_project_state(session_id: str, current_user: dict = Depends(get_current_user)):
    orchestrator = ProjectOrchestrator(current_user["user_id"], session_id)
    state = await asyncio.to_thread(orchestrator.get_full_state)
    return success_response(data=state)

@api.post("/project/reset")
async def reset_project(request: ProjectLoadRequestPhase6, current_user: dict = Depends(get_current_user)):
    orchestrator = ProjectOrchestrator(current_user["user_id"], request.session_id)
    await asyncio.to_thread(orchestrator.reset_project)
    return success_response(message="Project reset.")

# ============================================================================
# INCLUDE API ROUTER
# ============================================================================
app.include_router(api)
app.include_router(auth_router)
app.include_router(content_router)
app.include_router(billing_router)
app.include_router(beat_router)
app.include_router(lyrics_router)
app.include_router(media_router)
app.include_router(release_router)
app.include_router(analytics_router)
app.include_router(social_router)

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

