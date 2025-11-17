"""
Legacy upload endpoint for video files
Moved from content.py to isolate legacy upload code
"""

import os
import uuid
import subprocess
import re
from pathlib import Path
from typing import Optional

from fastapi import File, UploadFile, Form

from project_memory import get_or_create_project_memory

# These functions will be imported from content.py when this module is used
def setup_upload_video_endpoint(content_router, get_session_media_path, success_response, error_response, logger):
    """
    Setup the upload_video endpoint on the provided content_router
    """
    @content_router.post("/upload-video")
    async def upload_video(
        file: UploadFile = File(...),
        session_id: Optional[str] = Form(None)
    ):
        """Upload video file and extract audio + transcript"""
        session_id = session_id or str(uuid.uuid4())
        session_path = get_session_media_path(session_id)
        videos_dir = session_path / "videos"
        videos_dir.mkdir(exist_ok=True, parents=True)
        
        try:
            # Validate file extension
            if not file.filename:
                return error_response("No filename provided")
            
            allowed_extensions = ('.mp4', '.mov', '.avi', '.mkv')
            if not file.filename.lower().endswith(allowed_extensions):
                return error_response("Invalid video format. Only .mp4, .mov, .avi, .mkv allowed")
            
            # Save video file
            video_file = videos_dir / file.filename
            content = await file.read()
            
            # Validate file size (100MB limit)
            max_size = 100 * 1024 * 1024
            if len(content) > max_size:
                return error_response("File size exceeds 100MB limit")
            
            with open(video_file, 'wb') as f:
                f.write(content)
            
            # Extract audio track using ffmpeg
            audio_file = videos_dir / f"{Path(file.filename).stem}.wav"
            try:
                subprocess.run(
                    ['ffmpeg', '-i', str(video_file), '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', str(audio_file)],
                    capture_output=True,
                    check=True,
                    timeout=60
                )
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.warning(f"FFmpeg audio extraction failed: {e}")
                # Continue without audio extraction
            
            # Get video duration using ffmpeg
            duration = 0
            fps = 30  # Default
            try:
                result = subprocess.run(
                    ['ffmpeg', '-i', str(video_file)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # Parse duration from stderr output
                duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', result.stderr)
                if duration_match:
                    hours, minutes, seconds, centiseconds = duration_match.groups()
                    duration = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centiseconds) / 100
            except Exception as e:
                logger.warning(f"Duration extraction failed: {e}")
            
            # Extract transcript using OpenAI Whisper API (if available)
            transcript = ""
            api_key = os.getenv("OPENAI_API_KEY")
            
            if api_key and audio_file.exists():
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)
                    
                    with open(audio_file, 'rb') as audio:
                        transcript_response = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio,
                            language="en"
                        )
                        transcript = transcript_response.text
                except Exception as e:
                    logger.warning(f"Whisper transcript extraction failed: {e}")
                    transcript = f"[Transcript extraction failed: {str(e)}]"
            else:
                transcript = "[Transcript not available - OpenAI API key required]"
            
            # Save transcript to file
            transcript_file = videos_dir / f"{Path(file.filename).stem}_transcript.txt"
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(transcript)
            
            video_url = f"/media/{session_id}/videos/{file.filename}"
            
            # Update project memory
            memory = get_or_create_project_memory(session_id, Path("./media"))
            memory.add_asset("uploaded_video", video_url, {
                "filename": file.filename,
                "duration": duration,
                "fps": fps,
                "transcript": transcript
            })
            
            return success_response(
                data={
                    "file_url": video_url,
                    "transcript": transcript,
                    "duration": duration,
                    "fps": fps
                },
                message="Video uploaded and processed successfully"
            )
            
        except Exception as e:
            logger.error(f"Video upload failed: {e}", exc_info=True)
            return error_response(f"Video upload failed: {str(e)}")

