"""
Legacy upload endpoint for vocal recordings
Moved from main.py to isolate legacy upload code
"""

import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from fastapi import File, UploadFile, Form, HTTPException
from pydub import AudioSegment

from project_memory import get_or_create_project_memory
from backend.legacy.upload.security import validate_audio_file

# These will be imported from main.py when this module is loaded
# We'll import them at the bottom after main.py is fully loaded to avoid circular imports

def setup_upload_recording_endpoint(api, get_session_media_path, MEDIA_DIR, log_endpoint_event, error_response, success_response):
    """
    Setup the upload_recording endpoint on the provided api router
    """
    @api.post("/recordings/upload")
    async def upload_recording(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
        """V20: Upload vocal recording with comprehensive validation"""
        session_id = session_id if session_id else str(uuid.uuid4())
        session_path = get_session_media_path(session_id)
        stems_path = session_path / "stems"
        stems_path.mkdir(exist_ok=True, parents=True)
        
        try:
            # Phase 1: Centralized audio validation
            try:
                await validate_audio_file(file)
            except HTTPException as he:
                log_endpoint_event("/recordings/upload", session_id, "error", {"error": he.detail})
                return error_response(
                    "Failed to upload recording",
                    status_code=500,
                    data={"session_id": session_id}
                )
            # Read file bytes for subsequent operations
            content = await file.read()
            
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
                    return error_response(
                        "Failed to upload recording",
                        status_code=500,
                        data={"session_id": session_id}
                    )
            except Exception as audio_error:
                # Clean up invalid file
                try:
                    file_path.unlink()
                except:
                    pass
                log_endpoint_event("/recordings/upload", session_id, "error", {"error": f"Audio validation failed: {str(audio_error)}"})
                return error_response(
                    "Failed to upload recording",
                    status_code=500,
                    data={"session_id": session_id}
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
                    "filename": file.filename,
                    "path": str(file_path),
                    "url": final_url,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                message="Recording uploaded"
            )
        
        except Exception as e:
            log_endpoint_event("/recordings/upload", session_id, "error", {"error": str(e)})
            return error_response(
                "Failed to upload recording",
                status_code=500,
                data={"session_id": session_id}
            )
