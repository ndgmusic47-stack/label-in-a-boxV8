"""
Analytics Service - Business logic for analytics metrics
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Constants
MEDIA_DIR = Path("./media")


class AnalyticsService:
    """Service class for analytics business logic"""
    
    def __init__(self):
        self.media_dir = MEDIA_DIR
    
    async def get_session_analytics(
        self,
        session_id: str,
        user_id: str,
        session_path: Path
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific session (safe demo metrics).
        
        Args:
            session_id: Session ID
            user_id: User ID
            session_path: Path to session media directory
            
        Returns:
            Dict with analytics data
        """
        project_file = session_path / "project.json"
        schedule_file = session_path / "schedule.json"
        
        # Safe defaults
        analytics = {
            "session_id": session_id,
            "stages_completed": 0,
            "files_created": 0,
            "scheduled_posts": 0,
            "estimated_reach": 0
        }
        
        # Load project.json if exists
        if project_file.exists():
            try:
                with open(project_file, 'r') as f:
                    project_data = json.load(f)
                    analytics["stages_completed"] = len(project_data.get("unlocked_stages", []))
                    analytics["files_created"] = len(project_data.get("assets", {}))
            except Exception as e:
                logger.warning(f"Failed to load project.json for analytics: {e}")
        
        # Load schedule.json if exists
        if schedule_file.exists():
            try:
                with open(schedule_file, 'r') as f:
                    schedule_data = json.load(f)
                    analytics["scheduled_posts"] = len(schedule_data)
                    analytics["estimated_reach"] = len(schedule_data) * 1000  # Demo metric
            except Exception as e:
                logger.warning(f"Failed to load schedule.json for analytics: {e}")
        
        return analytics
    
    async def get_dashboard_analytics(self) -> Dict[str, Any]:
        """
        Get dashboard analytics across all sessions (safe demo metrics).
        
        Returns:
            Dict with dashboard analytics data
        """
        all_sessions = list(self.media_dir.glob("*/project.json"))
        
        total_projects = len(all_sessions)
        total_beats = 0
        total_songs = 0
        total_releases = 0
        
        for session_file in all_sessions:
            try:
                with open(session_file, 'r') as f:
                    project_data = json.load(f)
                    assets = project_data.get("assets", {})
                    if "beat" in assets:
                        total_beats += 1
                    if "lyrics" in assets:
                        total_songs += 1
                    if "master" in assets or "mix" in assets:
                        total_releases += 1
            except Exception as e:
                logger.warning(f"Failed to load project file {session_file} for dashboard analytics: {e}")
        
        return {
            "dashboard": {
                "total_projects": total_projects,
                "total_beats": total_beats,
                "total_songs": total_songs,
                "total_releases": total_releases,
                "platform_reach": total_projects * 5000  # Demo metric
            }
        }

