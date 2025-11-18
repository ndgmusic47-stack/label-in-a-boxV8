"""
Project Orchestrator for Label-in-a-Box Phase 6
Manages project state machine and auto-save/load functionality
"""

import json
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
    
    def load_project(self) -> Dict:
        """
        Load project.json from disk.
        Returns project data or raises FileNotFoundError if missing.
        """
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project not found: {self.project_path}")
        
        try:
            with open(self.project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded project for session {self.session_id}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse project.json: {e}")
            raise ValueError(f"Invalid project.json format: {e}")
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            raise
    
    def save_project(self, data: Dict):
        """
        Save project data to disk.
        Updates updated_at timestamp automatically.
        """
        data["updated_at"] = datetime.now().isoformat()
        
        # Ensure created_at exists if this is a new project
        if "created_at" not in data:
            data["created_at"] = datetime.now().isoformat()
        
        # Ensure session_id matches
        data["session_id"] = self.session_id
        # Ensure user_id is included
        data["user_id"] = self.user_id
        
        try:
            with open(self.project_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved project for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            raise
    
    def update_stage(self, stage_name: str, payload: Dict):
        """
        Update a specific stage in the project.
        Merges payload into existing stage data.
        """
        try:
            # Load existing project or create new structure
            try:
                project_data = self.load_project()
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
            
            # Save updated project
            self.save_project(project_data)
            
            logger.info(f"Updated stage '{stage_name}' for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to update stage '{stage_name}': {e}")
            raise
    
    def get_stage(self, stage_name: str) -> Optional[Dict]:
        """
        Get data for a specific stage.
        Returns None if stage doesn't exist or project not found.
        """
        try:
            project_data = self.load_project()
            stages = project_data.get("stages", {})
            return stages.get(stage_name)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get stage '{stage_name}': {e}")
            return None
    
    def get_full_state(self) -> Dict:
        """
        Get complete project state.
        Returns project data or empty structure if project not found.
        """
        try:
            return self.load_project()
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
    
    def reset_project(self):
        """
        Reset project by deleting project.json and recreating empty structure.
        """
        try:
            # Delete existing project file
            if self.project_path.exists():
                self.project_path.unlink()
                logger.info(f"Deleted project.json for session {self.session_id}")
            
            # Create empty structure
            empty_project = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "stages": {}
            }
            
            self.save_project(empty_project)
            logger.info(f"Reset project for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to reset project: {e}")
            raise

