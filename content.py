"""
V23 ContentStage MVP Backend
Handles video idea generation, upload, analysis, caption generation, and scheduling.
"""

import os
import uuid
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import requests
from pydub import AudioSegment

from project_memory import get_or_create_project_memory
from social_scheduler import SocialScheduler

logger = logging.getLogger(__name__)

# Create router for content endpoints
content_router = APIRouter(prefix="/api/content", tags=["content"])

# Helper functions
def get_session_media_path(session_id: str) -> Path:
    """Get media path for session"""
    path = Path("./media") / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def success_response(data: Optional[dict] = None, message: str = "Success"):
    """Standardized success response (Phase 1)"""
    return {"status": "success", "data": data or {}, "message": message}

def error_response(error: str, status_code: int = 400):
    """Standardized error response (Phase 1)"""
    logger.error(f"Error response: {error}")
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "data": {}, "message": error}
    )

# ============================================================================
# STEP 1: POST /content/idea - Generate Video Idea
# ============================================================================

class IdeaRequest(BaseModel):
    session_id: Optional[str] = None
    title: Optional[str] = None
    lyrics: Optional[str] = None
    mood: Optional[str] = None
    genre: Optional[str] = None

@content_router.post("/idea")
async def generate_video_idea(request: IdeaRequest = Body(default=None)):
    """Generate a simple, practical video idea"""
    if request is None:
        request = IdeaRequest()
    
    session_id = request.session_id or str(uuid.uuid4())
    title = request.title or "My Track"
    lyrics = request.lyrics or ""
    mood = request.mood or "energetic"
    genre = request.genre or "hip hop"
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Simple fallback idea
    fallback_idea = {
        "idea": "Do a talking-head explaining the meaning behind the chorus.",
        "hook": "This line hits harder when you know the story behind it...",
        "script": "Say one or two lines explaining what inspired the track.",
        "visual": "Record in a quiet space, chest-up, with your phone facing you."
    }
    
    if not api_key:
        logger.info("OpenAI API key not configured - using fallback idea")
        return success_response(data=fallback_idea, message="Video idea generated")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Generate a simple, practical video idea for a {mood} {genre} track titled "{title}".

Rules:
- NO cinematic jargon
- NO complex directions
- NO multi-shot filming
- Keep everything short and simple
- Make it practical and easy to film with a phone

Return a JSON object with:
- idea: A one-sentence description of what video to make
- hook: A simple opening line (first 3 seconds)
- script: One or two lines to say
- visual: Simple filming instructions (one sentence)

Example format:
{{
  "idea": "Do a talking-head explaining the meaning behind the chorus.",
  "hook": "This line hits harder when you know the story behind it...",
  "script": "Say one or two lines explaining what inspired the track.",
  "visual": "Record in a quiet space, chest-up, with your phone facing you."
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a practical video content creator. Generate simple, actionable video ideas that are easy to film with a phone."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content.strip()
        idea_data = json.loads(result_text)
        
        # Validate structure
        if not all(key in idea_data for key in ["idea", "hook", "script", "visual"]):
            return success_response(data=fallback_idea, message="Video idea generated (fallback)")
        
        return success_response(data=idea_data, message="Video idea generated")
        
    except Exception as e:
        logger.warning(f"OpenAI idea generation failed: {e} - using fallback")
        return success_response(data=fallback_idea, message="Video idea generated (fallback)")

# ============================================================================
# STEP 2: POST /content/upload-video - LEGACY UPLOAD (moved to backend/legacy/upload/)
# ============================================================================

from backend.legacy.upload.video import setup_upload_video_endpoint
setup_upload_video_endpoint(content_router, get_session_media_path, success_response, error_response, logger)

# ============================================================================
# STEP 3: POST /content/analyze - Analyze Video for Viral Score
# ============================================================================

class AnalyzeRequest(BaseModel):
    transcript: str = Field(..., description="Video transcript")
    title: Optional[str] = None
    lyrics: Optional[str] = None
    mood: Optional[str] = None
    genre: Optional[str] = None

@content_router.post("/analyze")
async def analyze_video(request: AnalyzeRequest):
    """Analyze video transcript and return viral score + improvements"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Fallback analysis
    fallback_analysis = {
        "score": 70,
        "summary": "Good energy, could improve hook strength.",
        "improvements": [
            "Start speaking faster in the first second.",
            "Increase energy on key phrase.",
            "Try brighter lighting."
        ],
        "suggested_hook": "Let me tell you why this line matters...",
        "thumbnail_suggestion": "Use frame at 0:01"
    }
    
    if not api_key:
        logger.info("OpenAI API key not configured - using fallback analysis")
        return success_response(data=fallback_analysis, message="Video analyzed")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Analyze this video transcript for viral potential on TikTok/Instagram Reels.

Transcript: {request.transcript[:1000]}
Title: {request.title or "Unknown"}
Lyrics: {request.lyrics or "N/A"}
Mood: {request.mood or "Unknown"}
Genre: {request.genre or "Unknown"}

Evaluate using these heuristics:
1. Hook strength (first 1.5 seconds)
2. First 1.5s engagement
3. Emotion/clarity
4. Simplicity
5. Retention potential
6. TikTok fit

Return a JSON object with:
- score: Number 0-100 (viral score)
- summary: One sentence summary
- improvements: Array of 3 specific, actionable improvement suggestions
- suggested_hook: A better opening line if needed
- thumbnail_suggestion: Simple thumbnail suggestion

Example format:
{{
  "score": 74,
  "summary": "Strong energy, intro slightly slow.",
  "improvements": [
    "Start speaking faster in the first second.",
    "Increase energy on key phrase.",
    "Try brighter lighting."
  ],
  "suggested_hook": "Let me tell you why this line matters...",
  "thumbnail_suggestion": "Use frame at 0:01"
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a viral content analyst. Analyze videos for TikTok/Instagram Reels potential and provide actionable feedback."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content.strip()
        analysis_data = json.loads(result_text)
        
        # Validate structure
        if "score" not in analysis_data:
            return success_response(data=fallback_analysis, message="Video analyzed (fallback)")
        
        return success_response(data=analysis_data, message="Video analyzed successfully")
        
    except Exception as e:
        logger.warning(f"Video analysis failed: {e} - using fallback")
        return success_response(data=fallback_analysis, message="Video analyzed (fallback)")

# ============================================================================
# STEP 4: POST /content/generate-text - Generate Captions & Hashtags
# ============================================================================

class GenerateTextRequest(BaseModel):
    session_id: Optional[str] = None
    title: Optional[str] = None
    transcript: Optional[str] = None
    lyrics: Optional[str] = None
    mood: Optional[str] = None
    genre: Optional[str] = None

@content_router.post("/generate-text")
async def generate_text(request: GenerateTextRequest):
    """Generate captions, hashtags, hooks, posting strategy, and content ideas"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Fallback text pack
    fallback_text = {
        "captions": [
            "New music alert! 🎵 Check out my latest track!",
            "Behind the scenes of my new release 🎧",
            "This one hits different 🔥"
        ],
        "hashtags": ["#np22", "#mindsetmusic", "#motivation", "#newmusic", "#hiphop"],
        "hooks": [
            "You need to hear this...",
            "This line hits different when you know the story...",
            "Let me tell you why this matters..."
        ],
        "posting_strategy": "Post between 5-7pm for maximum engagement.",
        "ideas": [
            "Do a behind-the-scenes video",
            "Share the story behind the lyrics",
            "Create a quick tutorial"
        ]
    }
    
    if not api_key:
        logger.info("OpenAI API key not configured - using fallback text")
        return success_response(data=fallback_text, message="Content text generated")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Generate social media content for a {request.mood or "energetic"} {request.genre or "hip hop"} track titled "{request.title or "My Track"}".

Transcript: {request.transcript or "N/A"}
Lyrics: {request.lyrics or "N/A"}

Return a JSON object with:
- captions: Array of 3 different caption options
- hashtags: Array of 5-10 relevant hashtags
- hooks: Array of 3 hook options (opening lines)
- posting_strategy: One sentence posting strategy
- ideas: Array of 3 additional content ideas

Example format:
{{
  "captions": ["Caption 1", "Caption 2", "Caption 3"],
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "hooks": ["Hook 1", "Hook 2", "Hook 3"],
  "posting_strategy": "Post between 5-7pm.",
  "ideas": ["Idea 1", "Idea 2", "Idea 3"]
}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a social media content strategist. Generate engaging captions, hashtags, and content ideas for music promotion."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content.strip()
        text_data = json.loads(result_text)
        
        # Validate structure
        if not all(key in text_data for key in ["captions", "hashtags", "hooks", "posting_strategy", "ideas"]):
            return success_response(data=fallback_text, message="Content text generated (fallback)")
        
        return success_response(data=text_data, message="Content text generated successfully")
        
    except Exception as e:
        logger.warning(f"Text generation failed: {e} - using fallback")
        return success_response(data=fallback_text, message="Content text generated (fallback)")

# ============================================================================
# STEP 5: POST /content/schedule - Schedule Video via GETLATE API
# ============================================================================

class ScheduleRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    video_url: str = Field(..., description="Video file URL")
    caption: str = Field(..., description="Selected caption")
    hashtags: Optional[List[str]] = Field(default=[], description="Selected hashtags")
    platform: str = Field(default="tiktok", description="Platform (tiktok, shorts, reels)")
    schedule_time: str = Field(..., description="ISO datetime string for scheduling")

@content_router.post("/schedule")
async def schedule_video(request: ScheduleRequest):
    """Schedule video using GETLATE API"""
    session_id = request.session_id
    getlate_key = os.getenv("GETLATE_API_KEY")
    
    try:
        # Use SocialScheduler for GETLATE integration
        scheduler = SocialScheduler(session_id)
        
        # Combine caption and hashtags
        hashtag_string = " ".join(request.hashtags) if request.hashtags else ""
        full_caption = f"{request.caption}\n\n{hashtag_string}".strip()
        
        # Try GETLATE API if key available
        if getlate_key:
            result = scheduler.schedule_with_getlate(
                platform=request.platform,
                content=full_caption,
                scheduled_time=request.schedule_time,
                api_key=getlate_key,
                media_url=request.video_url,
                hashtags=request.hashtags
            )
            
            if result.get("success"):
                # Update project memory
                memory = get_or_create_project_memory(session_id, Path("./media"))
                memory.update("contentScheduled", True)
                memory.advance_stage("content", "analytics")
                
                return success_response(
                    data={
                        "post_id": result.get("post_id"),
                        "platform": request.platform,
                        "scheduled_time": request.schedule_time,
                        "status": "scheduled",
                        "provider": "getlate"
                    },
                    message="Video scheduled successfully via GetLate.dev"
                )
            else:
                logger.warning(f"GetLate API failed: {result.get('error')} - falling back to local")
        
        # FALLBACK: Local JSON storage
        session_path = get_session_media_path(session_id)
        schedule_file = session_path / "schedule.json"
        
        # Load existing schedule
        if schedule_file.exists():
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
        else:
            schedule = []
        
        # Create post ID
        post_id = f"{request.platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Append new post
        post = {
            "post_id": post_id,
            "platform": request.platform,
            "video_url": request.video_url,
            "caption": full_caption,
            "hashtags": request.hashtags,
            "scheduled_time": request.schedule_time,
            "created_at": datetime.now().isoformat(),
            "provider": "local",
            "status": "scheduled"
        }
        schedule.append(post)
        
        # Save
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        
        # Update project memory
        memory = get_or_create_project_memory(session_id, Path("./media"))
        memory.update("contentScheduled", True)
        memory.advance_stage("content", "analytics")
        
        return success_response(
            data={
                "post_id": post_id,
                "platform": request.platform,
                "scheduled_time": request.schedule_time,
                "status": "scheduled",
                "provider": "local"
            },
            message="Video scheduled locally (GetLate API key not configured)"
        )
        
    except Exception as e:
        logger.error(f"Video scheduling failed: {e}", exc_info=True)
        return error_response(f"Video scheduling failed: {str(e)}")

# ============================================================================
# POST /content/save-scheduled - Save Scheduled Post
# ============================================================================

class SaveScheduledRequest(BaseModel):
    sessionId: str = Field(..., description="Session ID")
    platform: str = Field(..., description="Platform (tiktok, shorts, reels)")
    dateTime: Optional[str] = Field(None, description="ISO datetime string")
    time: Optional[str] = Field(None, description="ISO datetime string (legacy)")
    caption: Optional[str] = Field(None, description="Caption text")

@content_router.post("/save-scheduled")
async def save_scheduled(request: SaveScheduledRequest):
    """Save scheduled post to project memory"""
    session_id = request.sessionId
    
    # Validate required fields
    if not request.platform:
        return error_response("Platform is required")
    
    # Use dateTime if provided, otherwise fall back to time
    scheduled_time = request.dateTime or request.time
    if not scheduled_time:
        return error_response("dateTime is required")
    
    session_path = get_session_media_path(session_id)
    schedule_file = session_path / "schedule.json"
    
    # Load existing schedule
    if schedule_file.exists():
        with open(schedule_file, 'r') as f:
            schedule = json.load(f)
    else:
        schedule = []
    
    # Create post entry
    post = {
        "post_id": f"{request.platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "platform": request.platform,
        "dateTime": scheduled_time,
        "time": scheduled_time,  # Keep for backward compatibility
        "caption": request.caption or "",
        "created_at": datetime.now().isoformat(),
        "status": "scheduled"
    }
    schedule.append(post)
    
    # Save
    with open(schedule_file, 'w') as f:
        json.dump(schedule, f, indent=2)
    
    # Update project memory
    memory = get_or_create_project_memory(session_id, Path("./media"))
    memory.update("contentScheduled", True)
    
    return success_response(
        data={"post_id": post["post_id"], "status": "saved"},
        message="Scheduled post saved"
    )

# ============================================================================
# GET /content/get-scheduled - Get Scheduled Posts
# ============================================================================

@content_router.get("/get-scheduled")
async def get_scheduled(session_id: str = Query(..., description="Session ID")):
    """Get all scheduled posts for a session"""
    session_path = get_session_media_path(session_id)
    schedule_file = session_path / "schedule.json"
    
    if not schedule_file.exists():
        return success_response(data=[], message="No scheduled posts")
    
    try:
        with open(schedule_file, 'r') as f:
            schedule = json.load(f)
        return success_response(data=schedule, message="Scheduled posts retrieved")
    except Exception as e:
        logger.error(f"Failed to load schedule: {e}")
        return success_response(data=[], message="No scheduled posts")

