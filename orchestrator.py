"""
Project Orchestrator for Label-in-a-Box Phase 6
Manages project state machine and auto-save/load functionality
"""

import json
import os
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ProjectOrchestrator:
    """
    Orchestrates project state across all stages.
    Manages a unified project.json file with stage-based state tracking.
    """
    
    def __init__(self, user_id: str, session_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.project_path = Path(f"./media/{user_id}/{session_id}/project.json")
        self.project_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
    
    async def load_project(self) -> Dict:
        """
        Load project.json from disk.
        Returns project data or raises FileNotFoundError if missing.
        """
        async with self._lock:
            default = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "stages": {}
            }
            
            if not self.project_path.exists():
                return default
            
            try:
                with open(self.project_path, 'r', encoding='utf-8') as f:
                    data = await asyncio.to_thread(json.load, f)
                
                if "user_id" not in data:
                    data["user_id"] = self.user_id
                if "session_id" not in data:
                    data["session_id"] = self.session_id
                if "created_at" not in data:
                    data["created_at"] = datetime.utcnow().isoformat()
                if "updated_at" not in data:
                    data["updated_at"] = datetime.utcnow().isoformat()
                if "stages" not in data or not isinstance(data["stages"], dict):
                    data["stages"] = {}
                
                logger.info(f"Loaded project for session {self.session_id}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse project.json: {e}")
                await self.save_project(default)
                return default
            except Exception as e:
                logger.error(f"Failed to load project: {e}")
                raise
    
    async def save_project(self, data: Dict):
        """
        Save project data to disk.
        Updates updated_at timestamp automatically.
        """
        data["updated_at"] = datetime.utcnow().isoformat()
        
        async with self._lock:
            try:
                temp_path = self.project_path.with_suffix(".json.tmp")
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self.project_path)
                logger.info(f"Saved project for session {self.session_id}")
            except Exception as e:
                logger.error(f"Failed to save project: {e}")
                raise
    
    async def update_stage(self, stage_name: str, payload: Dict):
        """
        Update a specific stage in the project.
        Merges payload into existing stage data.
        """
        try:
            # Load existing project or create new structure
            try:
                project_data = await self.load_project()
            except FileNotFoundError:
                # Create new project structure
                project_data = {
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "stages": {}
                }
            
            # Ensure stages dict exists
            if "stages" not in project_data:
                project_data["stages"] = {}
            
            # Initialize stage if it doesn't exist
            if stage_name not in project_data["stages"]:
                project_data["stages"][stage_name] = {}
            
            # Merge payload into stage data
            project_data["stages"][stage_name].update(payload)
            
            # Update timestamp
            project_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated project
            await self.save_project(project_data)
            
            logger.info(f"Updated stage '{stage_name}' for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to update stage '{stage_name}': {e}")
            raise
    
    async def get_stage(self, stage_name: str) -> Optional[Dict]:
        """
        Get data for a specific stage.
        Returns None if stage doesn't exist or project not found.
        """
        try:
            project_data = await self.load_project()
            stages = project_data.get("stages", {})
            return stages.get(stage_name)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get stage '{stage_name}': {e}")
            return None
    
    async def get_full_state(self) -> Dict:
        """
        Get complete project state.
        Returns project data or empty structure if project not found.
        """
        try:
            return await self.load_project()
        except FileNotFoundError:
            # Return empty structure matching expected format
            empty_state = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "stages": {}
            }
            return empty_state
        except Exception as e:
            logger.error(f"Failed to get full state: {e}")
            # Return minimal structure on error
            error_state = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "stages": {},
                "error": str(e)
            }
            return error_state
    
    async def reset_project(self):
        """
        Reset project by deleting project.json and recreating empty structure.
        """
        def _delete_file():
            if self.project_path.exists():
                self.project_path.unlink()
        
        def _clean_media_dir():
            media_dir = self.project_path.parent
            if media_dir.exists():
                for item in media_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
        
        try:
            async with self._lock:
                # Clean session media folder
                await asyncio.to_thread(_clean_media_dir)
                # Delete existing project file
                await asyncio.to_thread(_delete_file)
                logger.info(f"Deleted project.json for session {self.session_id}")
            
            # Create empty structure
            empty_project = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "stages": {}
            }
            
            await self.save_project(empty_project)
            logger.info(f"Reset project for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to reset project: {e}")
            raise

