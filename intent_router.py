"""
Intent Router - Interprets natural language commands and routes to appropriate actions
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from project_memory import ProjectMemory


class IntentRouter:
    """
    Intelligent command interpreter that routes voice/text commands
    to the appropriate backend action.
    """
    
    def __init__(self, session_id: str, media_dir: Path):
        self.session_id = session_id
        self.memory = ProjectMemory(session_id, media_dir)
        
        # Intent patterns mapped to actions
        self.intent_patterns = {
            # Beat modification
            r"(make|set|change).*beat.*(faster|slower|speed|tempo)": "modify_beat_tempo",
            r"(add|increase|boost).*(bass|low end)": "modify_beat_bass",
            r"(reduce|decrease|lower).*(bass|low end)": "reduce_beat_bass",
            
            # Mix controls
            r"(turn up|increase|boost).*(vocal|voice)": "increase_vocals",
            r"(turn down|reduce|lower).*(vocal|voice)": "reduce_vocals",
            r"(add|more).*(reverb|echo)": "add_reverb",
            r"(remove|less).*(reverb|echo)": "reduce_reverb",
            r"(brighten|add treble|more high)": "brighten_mix",
            r"(darken|reduce treble|less high)": "darken_mix",
            
            # Content generation
            r"generate.*(tiktok|video|clip)": "generate_video_content",
            r"create.*(caption|post|hook)": "generate_social_content",
            r"write.*(\d+).*(caption|post|hook)": "generate_multiple_captions",
            
            # Workflow navigation
            r"(go to|move to|next).*(stage|step)": "next_stage",
            r"(back|previous|return).*(stage|step)": "previous_stage",
            r"(show|open).*(beat|lyric|upload|mix|release|content|analytics)": "navigate_stage",
            
            # Project info
            r"(what|show).*(progress|status|stage)": "get_project_status",
            r"(what|which).*(current|active).*stage": "get_current_stage",
        }
    
    def parse_intent(self, command: str) -> Dict[str, Any]:
        """
        Parse natural language command and determine intent + parameters.
        
        Args:
            command: Natural language command from user
            
        Returns:
            Dict with action, parameters, and confidence
        """
        command_lower = command.lower().strip()
        
        # Try to match against known patterns
        for pattern, action in self.intent_patterns.items():
            if re.search(pattern, command_lower):
                return self._build_intent_response(action, command_lower, pattern)
        
        # If no pattern matches, try keyword-based fallback
        return self._keyword_fallback(command_lower)
    
    def _build_intent_response(self, action: str, command: str, pattern: str) -> Dict[str, Any]:
        """Build intent response with extracted parameters."""
        response = {
            "action": action,
            "parameters": {},
            "confidence": 0.9,
            "original_command": command
        }
        
        # Extract numeric parameters
        numbers = re.findall(r'\d+', command)
        if numbers:
            response["parameters"]["value"] = int(numbers[0])
        
        # Extract direction for tempo/level changes
        if any(word in command for word in ["faster", "speed up", "increase", "more", "boost", "up", "add"]):
            response["parameters"]["direction"] = "increase"
        elif any(word in command for word in ["slower", "slow down", "decrease", "less", "reduce", "down", "lower"]):
            response["parameters"]["direction"] = "decrease"
        
        # Extract stage names
        stages = ["beat", "lyrics", "upload", "mix", "release", "content", "analytics"]
        for stage in stages:
            if stage in command:
                response["parameters"]["stage"] = stage
                break
        
        return response
    
    def _keyword_fallback(self, command: str) -> Dict[str, Any]:
        """Fallback keyword-based intent detection."""
        keywords = {
            "faster": {"action": "modify_beat_tempo", "parameters": {"direction": "increase"}},
            "slower": {"action": "modify_beat_tempo", "parameters": {"direction": "decrease"}},
            "louder": {"action": "increase_vocals", "parameters": {}},
            "quieter": {"action": "reduce_vocals", "parameters": {}},
            "next": {"action": "next_stage", "parameters": {}},
            "back": {"action": "previous_stage", "parameters": {}},
        }
        
        for keyword, intent in keywords.items():
            if keyword in command:
                return {
                    **intent,
                    "confidence": 0.6,
                    "original_command": command
                }
        
        return {
            "action": "unknown",
            "parameters": {},
            "confidence": 0.0,
            "original_command": command,
            "message": "I didn't understand that command. Try being more specific."
        }
    
    def execute_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the parsed intent and return result.
        
        Args:
            intent: Parsed intent from parse_intent()
            
        Returns:
            Execution result with status and voice response
        """
        action = intent.get("action")
        params = intent.get("parameters", {})
        params["current_intent_action"] = action
        
        # Route to appropriate handler
        handlers = {
            "modify_beat_tempo": self._handle_beat_tempo,
            "modify_beat_bass": self._handle_beat_bass,
            "reduce_beat_bass": self._handle_beat_bass,
            "increase_vocals": self._handle_vocal_level,
            "reduce_vocals": self._handle_vocal_level,
            "add_reverb": self._handle_reverb,
            "reduce_reverb": self._handle_reverb,
            "brighten_mix": self._handle_eq,
            "darken_mix": self._handle_eq,
            "generate_video_content": self._handle_video_generation,
            "generate_social_content": self._handle_social_generation,
            "generate_multiple_captions": self._handle_multiple_captions,
            "next_stage": self._handle_next_stage,
            "previous_stage": self._handle_previous_stage,
            "navigate_stage": self._handle_navigate_stage,
            "get_project_status": self._handle_project_status,
            "get_current_stage": self._handle_current_stage,
        }
        
        handler = handlers.get(action)
        if handler:
            return handler(params)
        
        return {
            "success": False,
            "message": "Command not supported yet",
            "voice_response": "I'm not sure how to do that yet. Try a different command."
        }
    
    # Intent handlers
    
    def _handle_beat_tempo(self, params: Dict) -> Dict[str, Any]:
        """Handle beat tempo modification."""
        current_action = params.get("current_intent_action", "")
        direction = params.get("direction", "increase")
        value = params.get("value", 10)
        
        current_tempo = self.memory.get("beat.tempo", 120)
        new_tempo = current_tempo + value if direction == "increase" else current_tempo - value
        new_tempo = max(60, min(200, new_tempo))  # Clamp to reasonable range
        
        self.memory.update("beat.tempo", new_tempo)
        
        direction_word = "increased" if direction == "increase" else "decreased"
        return {
            "success": True,
            "action": "modify_beat_tempo",
            "new_value": new_tempo,
            "voice_response": f"Beat tempo {direction_word} to {new_tempo} BPM",
            "department": "Echo"
        }
    
    def _handle_beat_bass(self, params: Dict) -> Dict[str, Any]:
        """Handle bass level modification."""
        current_action = params.get("current_intent_action", "")
        action_type = "increase" if "modify" in current_action else "reduce"
        
        self.memory.update("mix.bass_boost", action_type == "increase")
        
        response = "Added more bass to the beat" if action_type == "increase" else "Reduced the bass"
        return {
            "success": True,
            "action": "modify_bass",
            "voice_response": response,
            "department": "Echo"
        }
    
    def _handle_vocal_level(self, params: Dict) -> Dict[str, Any]:
        """Handle vocal level adjustment."""
        current_action = params.get("current_intent_action", "")
        current_level = self.memory.get("mix.vocal_level", 0)
        adjustment = 3 if "increase" in current_action else -3
        new_level = max(-12, min(12, current_level + adjustment))
        
        self.memory.update("mix.vocal_level", new_level)
        
        return {
            "success": True,
            "action": "adjust_vocals",
            "new_value": new_level,
            "voice_response": f"Vocal level adjusted by {adjustment} dB",
            "department": "Tone"
        }
    
    def _handle_reverb(self, params: Dict) -> Dict[str, Any]:
        """Handle reverb adjustment."""
        current_action = params.get("current_intent_action", "")
        action_type = "add" if "add" in current_action else "reduce"
        current_reverb = self.memory.get("mix.reverb_amount", 0.3)
        new_reverb = min(1.0, current_reverb + 0.2) if action_type == "add" else max(0.0, current_reverb - 0.2)
        
        self.memory.update("mix.reverb_amount", new_reverb)
        
        return {
            "success": True,
            "action": "adjust_reverb",
            "new_value": new_reverb,
            "voice_response": f"Reverb {'increased' if action_type == 'add' else 'decreased'}",
            "department": "Tone"
        }
    
    def _handle_eq(self, params: Dict) -> Dict[str, Any]:
        """Handle EQ adjustment."""
        current_action = params.get("current_intent_action", "")
        action_type = "brighten" if "brighten" in current_action else "darken"
        
        self.memory.update("mix.eq_preset", action_type)
        
        return {
            "success": True,
            "action": "adjust_eq",
            "voice_response": f"Mix {action_type}ed with EQ adjustment",
            "department": "Tone"
        }
    
    def _handle_video_generation(self, params: Dict) -> Dict[str, Any]:
        """Handle video content generation request."""
        count = params.get("value", 3)
        
        return {
            "success": True,
            "action": "generate_videos",
            "count": count,
            "voice_response": f"I'll create {count} video clips for you",
            "department": "Vee",
            "redirect_to": "content"
        }
    
    def _handle_social_generation(self, params: Dict) -> Dict[str, Any]:
        """Handle social content generation request."""
        return {
            "success": True,
            "action": "generate_social",
            "voice_response": "Creating social media content for you",
            "department": "Vee",
            "redirect_to": "content"
        }
    
    def _handle_multiple_captions(self, params: Dict) -> Dict[str, Any]:
        """Handle request for multiple captions."""
        count = params.get("value", 5)
        
        return {
            "success": True,
            "action": "generate_captions",
            "count": count,
            "voice_response": f"Writing {count} caption variations",
            "department": "Vee",
            "redirect_to": "content"
        }
    
    def _handle_next_stage(self, params: Dict) -> Dict[str, Any]:
        """Navigate to next stage in workflow."""
        stages = ["beat", "lyrics", "upload", "mix", "release", "content", "analytics"]
        current = self.memory.get("workflow.current_stage", "beat")
        
        try:
            current_idx = stages.index(current)
            next_stage = stages[min(current_idx + 1, len(stages) - 1)]
            self.memory.update("workflow.current_stage", next_stage)
            
            return {
                "success": True,
                "action": "navigate",
                "stage": next_stage,
                "voice_response": f"Moving to {next_stage.title()} stage",
                "department": self._get_department_for_stage(next_stage)
            }
        except ValueError:
            return {"success": False, "message": "Invalid current stage"}
    
    def _handle_previous_stage(self, params: Dict) -> Dict[str, Any]:
        """Navigate to previous stage in workflow."""
        stages = ["beat", "lyrics", "upload", "mix", "release", "content", "analytics"]
        current = self.memory.get("workflow.current_stage", "beat")
        
        try:
            current_idx = stages.index(current)
            prev_stage = stages[max(current_idx - 1, 0)]
            self.memory.update("workflow.current_stage", prev_stage)
            
            return {
                "success": True,
                "action": "navigate",
                "stage": prev_stage,
                "voice_response": f"Going back to {prev_stage.title()} stage",
                "department": self._get_department_for_stage(prev_stage)
            }
        except ValueError:
            return {"success": False, "message": "Invalid current stage"}
    
    def _handle_navigate_stage(self, params: Dict) -> Dict[str, Any]:
        """Navigate to specific stage."""
        target_stage = params.get("stage")
        if not target_stage:
            return {"success": False, "message": "No stage specified"}
        
        self.memory.update("workflow.current_stage", target_stage)
        
        return {
            "success": True,
            "action": "navigate",
            "stage": target_stage,
            "voice_response": f"Opening {target_stage.title()} workspace",
            "department": self._get_department_for_stage(target_stage)
        }
    
    def _handle_project_status(self, params: Dict) -> Dict[str, Any]:
        """Get current project status."""
        current_stage = self.memory.get("workflow.current_stage", "beat")
        completed_stages = self.memory.get("workflow.completed_stages", [])
        
        return {
            "success": True,
            "action": "get_status",
            "current_stage": current_stage,
            "completed_stages": completed_stages,
            "voice_response": f"You're at the {current_stage.title()} stage with {len(completed_stages)} stages completed",
            "department": "Nova"
        }
    
    def _handle_current_stage(self, params: Dict) -> Dict[str, Any]:
        """Get current active stage."""
        current_stage = self.memory.get("workflow.current_stage", "beat")
        
        return {
            "success": True,
            "action": "get_current_stage",
            "stage": current_stage,
            "voice_response": f"Currently at {current_stage.title()} stage",
            "department": "Nova"
        }
    
    def _get_department_for_stage(self, stage: str) -> str:
        """Map stage to department voice."""
        stage_departments = {
            "beat": "Echo",
            "lyrics": "Lyrica",
            "upload": "Nova",
            "mix": "Tone",
            "release": "Aria",
            "content": "Vee",
            "analytics": "Pulse"
        }
        return stage_departments.get(stage, "Nova")
