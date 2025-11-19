"""
Media router for file upload and mixing endpoints
"""
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models.mix import CleanMixRequest
from services.mix_service import MixService
from utils.shared_utils import require_feature_pro, get_session_media_path
from backend.orchestrator import ProjectOrchestrator
from backend.utils.responses import success_response

logger = logging.getLogger(__name__)

# Create router with /api prefix (will be included in main.py)
media_router = APIRouter(prefix="/api")


@media_router.post("/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clean audio upload endpoint - receives file, saves to media/{session_id}/recordings/, returns file URL"""
    # Phase 8A: Feature gate for clean upload
    deny = await require_feature_pro(current_user, feature="upload", endpoint="/upload-audio", db=db)
    if deny is not None:
        return deny
    
    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    user_id = current_user.get("user_id")
    
    # Create directory structure with user_id
    recordings_dir = Path("./media") / user_id / session_id / "recordings"
    file_url = f"/media/{user_id}/{session_id}/recordings/{file.filename}"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = recordings_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Phase 6: Auto-save to orchestrator
    orchestrator = ProjectOrchestrator(user_id, session_id)
    orchestrator.update_stage("vocals", {
        "vocal_url": file_url,
        "completed": True
    })
    
    return success_response(
        data={
            "session_id": session_id,
            "file_url": file_url
        },
        message="Vocal uploaded"
    )


@media_router.post("/mix/run-clean")
async def run_clean_mix(
    request: CleanMixRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clean mix with DSP processing: overlay processed vocal on beat"""
    # Phase 8A: Feature gate for clean mix
    deny = await require_feature_pro(current_user, feature="mix", endpoint="/mix/run-clean", db=db)
    if deny is not None:
        return deny
    
    # Use user_id from current_user, fallback to request.user_id
    user_id = current_user.get("user_id") or request.user_id
    if not user_id:
        from backend.utils.responses import error_response
        return error_response("MISSING_USER_ID", 400, "User ID is required")
    
    # Update request with user_id if not set
    if not request.user_id:
        request.user_id = user_id
    
    # Call service method
    return await MixService.run_clean_mix(request, user_id)


@media_router.post("/mix/{user_id}/{session_id}")
async def mix_audio(user_id: str, session_id: str):
    """Basic mix endpoint using apply_basic_mix"""
    return await MixService.mix_audio(user_id, session_id)

