from typing import Optional
from fastapi import UploadFile, HTTPException


ALLOWED_AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac")
MAX_AUDIO_BYTES = 50 * 1024 * 1024  # 50 MB


async def validate_audio_file(file: UploadFile) -> None:
    """
    Raise HTTPException if file extension or size is invalid.
    Ensures the UploadFile stream is reset after reading.
    """
    filename = file.filename or ""
    lower = filename.lower()
    if not lower.endswith(ALLOWED_AUDIO_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Invalid audio file. Only .wav, .mp3, .flac allowed")

    # Read bytes to validate size; then reset
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
    # Reset internal pointer so downstream handlers can read again
    await file.seek(0)


