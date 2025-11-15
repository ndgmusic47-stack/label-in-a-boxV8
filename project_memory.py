"""
Project Memory Layer for Label-in-a-Box v4
Persistent, contextual memory system for AI voices
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ProjectMemory:
    """
    Manages persistent project memory across sessions.
    Each project has a project.json file that stores:
    - Metadata (tempo, key, mood, genre)
    - All assets (beat, lyrics, stems, mix, release)
    - Chat logs and voice prompts
    - Analytics and metrics
    """
    
    def __init__(self, session_id: str, media_dir: Path, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.media_dir = media_dir
        if user_id:
            self.session_path = media_dir / user_id / session_id
        else:
            # Backward compatibility: use /media/{session_id}/ if no user_id
            self.session_path = media_dir / session_id
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.project_file = self.session_path / "project.json"
        self.project_data = self._load_or_create()
    
    def _load_or_create(self) -> Dict:
        """Load existing project or create new one"""
        if self.project_file.exists():
            with open(self.project_file, 'r') as f:
                return json.load(f)
        
        return {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {
                "tempo": None,
                "key": None,
                "mood": None,
                "genre": None,
                "artist_name": None,
                "track_title": None
            },
            "assets": {
                "beat": None,
                "lyrics": None,
                "vocals": [],
                "stems": [],
                "mix": None,
                "master": None,
                "release_pack": None,
                "cover_art": None,
                "clips": [],
                "reference_track": None
            },
            "reference_analysis": None,
            "chat_log": [],
            "voice_prompts": [],
            "analytics": {
                "streams": 0,
                "saves": 0,
                "shares": 0,
                "revenue": 0.0
            },
            "workflow_state": {
                "beat_done": False,
                "lyrics_done": False,
                "vocals_done": False,
                "mix_done": False,
                "release_done": False,
                "content_done": False
            },
            "workflow": {
                "current_stage": "beat",
                "completed_stages": [],
                "unlocked_stages": ["beat"]
            },
            "mix": {
                "vocal_level": 0,
                "reverb_amount": 0.3,
                "eq_preset": "neutral",
                "bass_boost": False
            },
            "beat": {
                "tempo": 120
            },
            "release": {
                "title": None,
                "artist": None,
                "genre": None,
                "mood": None,
                "release_date": None,
                "explicit": False,
                "cover_art": None,
                "metadata_path": None,
                "files": []
            }
        }
    
    def save(self):
        """Save project data to disk"""
        self.project_data["updated_at"] = datetime.now().isoformat()
        with open(self.project_file, 'w') as f:
            json.dump(self.project_data, f, indent=2)
        logger.info(f"Project memory saved for session {self.session_id}")
    
    def update_metadata(self, **kwargs):
        """Update project metadata"""
        for key, value in kwargs.items():
            if value is not None:
                self.project_data["metadata"][key] = value
        self.save()
    
    def add_asset(self, asset_type: str, file_url: str, metadata: Optional[Dict] = None):
        """Add asset to project memory"""
        if asset_type in ["vocals", "stems", "clips"]:
            self.project_data["assets"][asset_type].append({
                "url": file_url,
                "added_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            })
        else:
            self.project_data["assets"][asset_type] = {
                "url": file_url,
                "added_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
        self.save()
    
    def add_chat_message(self, speaker: str, message: str, voice_name: Optional[str] = None):
        """Log chat/voice interaction"""
        self.project_data["chat_log"].append({
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "voice": voice_name,
            "message": message
        })
        self.save()
    
    def add_voice_prompt(self, voice_name: str, prompt: str, response: str):
        """Log voice AI interaction"""
        self.project_data["voice_prompts"].append({
            "timestamp": datetime.now().isoformat(),
            "voice": voice_name,
            "prompt": prompt,
            "response": response
        })
        self.save()
    
    def set_reference_analysis(self, analysis: Dict):
        """Store reference track analysis"""
        self.project_data["reference_analysis"] = {
            "analyzed_at": datetime.now().isoformat(),
            **analysis
        }
        self.save()
    
    def update_workflow_state(self, **states):
        """Update workflow completion states"""
        for key, value in states.items():
            if key in self.project_data["workflow_state"]:
                self.project_data["workflow_state"][key] = value
        self.save()
    
    def update_analytics(self, **metrics):
        """Update analytics metrics"""
        for key, value in metrics.items():
            if key in self.project_data["analytics"]:
                self.project_data["analytics"][key] = value
        self.save()
    
    def get_context_summary(self) -> str:
        """Get AI-readable context summary for voice agents"""
        meta = self.project_data["metadata"]
        assets = self.project_data["assets"]
        workflow = self.project_data["workflow_state"]
        
        context = f"Project Session: {self.session_id}\n"
        
        if meta.get("track_title"):
            context += f"Track: '{meta['track_title']}'"
            if meta.get("artist_name"):
                context += f" by {meta['artist_name']}"
            context += "\n"
        
        if meta.get("tempo") or meta.get("key"):
            context += f"Music: "
            if meta.get("tempo"):
                context += f"{meta['tempo']} BPM"
            if meta.get("key"):
                context += f" in {meta['key']}"
            if meta.get("mood"):
                context += f", {meta['mood']} mood"
            context += "\n"
        
        completed_stages = [k.replace("_done", "") for k, v in workflow.items() if v]
        if completed_stages:
            context += f"Completed: {', '.join(completed_stages)}\n"
        
        if self.project_data["chat_log"]:
            context += f"Previous interactions: {len(self.project_data['chat_log'])} messages\n"
        
        return context
    
    def get_last_session_context(self) -> Optional[str]:
        """Get context from last session for continuity"""
        if not self.project_data["chat_log"]:
            return None
        
        meta = self.project_data["metadata"]
        last_tempo = meta.get("tempo")
        last_key = meta.get("key")
        
        if last_tempo and last_key:
            return f"Last time we were in {last_key} at {last_tempo} BPM—keep that energy?"
        elif last_tempo:
            return f"Last session we were at {last_tempo} BPM—want to keep that tempo?"
        
        return f"Welcome back! We have {len(self.project_data['chat_log'])} previous interactions."
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get nested value from project data using dot notation.
        Example: memory.get("metadata.tempo") or memory.get("workflow.current_stage")
        """
        keys = key.split(".")
        value = self.project_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def update(self, key: str, value: Any):
        """
        Update nested value in project data using dot notation.
        Example: memory.update("metadata.tempo", 120)
        """
        keys = key.split(".")
        data = self.project_data
        
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        data[keys[-1]] = value
        self.save()
    
    def advance_stage(self, completed_stage: str, next_stage: Optional[str] = None):
        """
        Track stage completion for analytics (stages are not locked in v4).
        
        Args:
            completed_stage: Stage that was just completed
            next_stage: Next stage (for tracking only, not locking)
        """
        stage_order = ["beat", "lyrics", "upload", "mix", "release", "content", "analytics"]
        
        # Mark stage as completed (for analytics/progress tracking only)
        if completed_stage not in self.project_data["workflow"]["completed_stages"]:
            self.project_data["workflow"]["completed_stages"].append(completed_stage)
        
        # Update current stage suggestion (not enforced)
        if next_stage is None:
            try:
                current_idx = stage_order.index(completed_stage)
                if current_idx < len(stage_order) - 1:
                    next_stage = stage_order[current_idx + 1]
            except (ValueError, IndexError):
                logger.warning(f"Could not determine next stage after {completed_stage}")
                next_stage = None
        
        if next_stage:
            self.project_data["workflow"]["current_stage"] = next_stage
        
        self.save()

def get_or_create_project_memory(session_id: str, media_dir: Path, user_id: Optional[str] = None) -> ProjectMemory:
    """Factory function to get or create project memory"""
    return ProjectMemory(session_id, media_dir, user_id)

def list_all_projects(media_dir: Path) -> List[Dict]:
    """List all projects with their metadata"""
    projects = []
    for item in media_dir.iterdir():
        if item.is_dir():
            project_file = item / "project.json"
            if project_file.exists():
                try:
                    with open(project_file, 'r') as f:
                        data = json.load(f)
                        projects.append({
                            "session_id": item.name,
                            "title": data["metadata"].get("track_title", "Untitled"),
                            "artist": data["metadata"].get("artist_name"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "workflow_complete": all(data["workflow_state"].values())
                        })
                except Exception as e:
                    logger.error(f"Error loading project {item.name}: {e}")
    
    return sorted(projects, key=lambda x: x["updated_at"], reverse=True)

def export_project(memory: ProjectMemory) -> Dict:
    """Export current project data for saving"""
    return {
        "stages": memory.project_data.get("workflow", {}),
        "release": memory.project_data.get("release", {}),
        "mix": memory.project_data.get("mix", {}),
        "content": memory.project_data.get("content", {}),
        "schedule": memory.project_data.get("schedule", {}),
        "upload": memory.project_data.get("upload", {}),
        "lyrics": memory.project_data.get("assets", {}).get("lyrics"),
        "beat": memory.project_data.get("beat", {}),
        "metadata": memory.project_data.get("metadata", {}),
        "assets": memory.project_data.get("assets", {}),
        "workflow_state": memory.project_data.get("workflow_state", {}),
        "analytics": memory.project_data.get("analytics", {}),
        "chat_log": memory.project_data.get("chat_log", []),
        "voice_prompts": memory.project_data.get("voice_prompts", []),
        "reference_analysis": memory.project_data.get("reference_analysis"),
    }

def import_project(data: Dict, memory: ProjectMemory):
    """Import project data into memory instance"""
    # Update all relevant sections
    if "stages" in data:
        memory.project_data["workflow"] = data["stages"]
    if "release" in data:
        memory.project_data["release"] = data["release"]
    if "mix" in data:
        memory.project_data["mix"] = data["mix"]
    if "content" in data:
        memory.project_data["content"] = data["content"]
    if "schedule" in data:
        memory.project_data["schedule"] = data["schedule"]
    if "upload" in data:
        memory.project_data["upload"] = data["upload"]
    if "lyrics" in data:
        if "assets" not in memory.project_data:
            memory.project_data["assets"] = {}
        memory.project_data["assets"]["lyrics"] = data["lyrics"]
    if "beat" in data:
        memory.project_data["beat"] = data["beat"]
    if "metadata" in data:
        memory.project_data["metadata"] = data["metadata"]
    if "assets" in data:
        memory.project_data["assets"] = data["assets"]
    if "workflow_state" in data:
        memory.project_data["workflow_state"] = data["workflow_state"]
    if "analytics" in data:
        memory.project_data["analytics"] = data["analytics"]
    if "chat_log" in data:
        memory.project_data["chat_log"] = data["chat_log"]
    if "voice_prompts" in data:
        memory.project_data["voice_prompts"] = data["voice_prompts"]
    if "reference_analysis" in data:
        memory.project_data["reference_analysis"] = data["reference_analysis"]
    
    memory.save()
