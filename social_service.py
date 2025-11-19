"""
Social Service - Business logic for social post scheduling
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from project_memory import get_or_create_project_memory
from social_scheduler import SocialScheduler

logger = logging.getLogger(__name__)

# Constants
MEDIA_DIR = Path("./media")


class SocialService:
    """Service class for social post scheduling business logic"""
    
    def __init__(self):
        self.media_dir = MEDIA_DIR
        self.getlate_key = os.getenv("GETLATE_API_KEY")
    
    async def get_platforms(self) -> Dict[str, Any]:
        """
        Get supported social media platforms.
        
        Returns:
            Dict with platforms list
        """
        return {
            "platforms": ["tiktok", "shorts", "reels"]
        }
    
    async def create_social_post(
        self,
        session_id: str,
        user_id: str,
        session_path: Path,
        platform: str,
        when_iso: str,
        caption: str
    ) -> Dict[str, Any]:
        """
        Schedule a social post using GetLate.dev API or local JSON fallback.
        
        Args:
            session_id: Session ID
            user_id: User ID
            session_path: Path to session media directory
            platform: Platform name (tiktok, shorts, reels)
            when_iso: ISO datetime string for scheduling
            caption: Post caption
            
        Returns:
            Dict with post scheduling result
        """
        # Set defaults if missing
        platform = platform or "tiktok"
        when_iso = when_iso or (datetime.now().isoformat() + "Z")
        caption = caption or "New music release!"
        
        if platform not in ["tiktok", "shorts", "reels"]:
            raise ValueError("Invalid platform. Use: tiktok, shorts, or reels")
        
        # Try GetLate.dev API if key is available
        if self.getlate_key:
            try:
                scheduler = SocialScheduler(session_id)
                result = await scheduler.schedule_with_getlate(
                    platform=platform,
                    content=caption,
                    scheduled_time=when_iso,
                    api_key=self.getlate_key
                )
                
                if result.get("success"):
                    # Update project memory
                    memory = await get_or_create_project_memory(session_id, self.media_dir)
                    await memory.advance_stage("content", "analytics")
                    
                    return {
                        "post_id": result.get("post_id"),
                        "platform": platform,
                        "scheduled_time": when_iso,
                        "provider": "getlate",
                        "status": "scheduled"
                    }
                else:
                    logger.warning(f"GetLate API failed: {result.get('error')} - falling back to local")
            except Exception as e:
                logger.warning(f"GetLate API error: {e} - falling back to local JSON")
        
        # FALLBACK: Local JSON storage
        schedule_file = session_path / "schedule.json"
        
        # Load existing schedule
        if schedule_file.exists():
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
        else:
            schedule = []
        
        # Append new post
        post_id = f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        post = {
            "post_id": post_id,
            "platform": platform,
            "when_iso": when_iso,
            "scheduled_time": when_iso,
            "caption": caption,
            "content": caption,
            "created_at": datetime.now().isoformat(),
            "provider": "local",
            "status": "scheduled"
        }
        schedule.append(post)
        
        # Save
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        
        # Update project memory
        memory = await get_or_create_project_memory(session_id, self.media_dir)
        await memory.advance_stage("content", "analytics")
        
        return {
            "post": post,
            "total_scheduled": len(schedule),
            "provider": "local",
            "status": "scheduled"
        }

