"""
Lyrics Service - Business logic for lyrics generation
"""
import os
import uuid
import json
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from openai import OpenAI
from project_memory import get_or_create_project_memory
from backend.orchestrator import ProjectOrchestrator
from utils.helpers import get_session_media_path, log_endpoint_event

logger = logging.getLogger(__name__)

# Constants
MEDIA_DIR = Path("./media")


class LyricsService:
    """Service class for lyrics generation business logic"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
    
    def detect_bpm(self, filepath: Path) -> int:
        """Detect BPM from audio file using aubio"""
        try:
            from aubio import tempo, source
            s = source(str(filepath))
            o = tempo()
            beats = []
            while True:
                samples, read = s()
                is_beat = o(samples)
                if is_beat:
                    beats.append(o.get_last_s())
                if read < s.hop_size:
                    break
            if len(beats) > 1:
                bpms = 60.0 / (beats[1] - beats[0])
                return int(bpms)
            return 140
        except Exception as e:
            logger.warning(f"BPM detection failed: {e} - using default 140")
            return 140
    
    def analyze_mood(self, filepath: Path) -> str:
        """Analyze mood from audio file - simple implementation"""
        # For now, return default mood as specified
        # In a full implementation, this could analyze spectral features, energy, etc.
        return "dark cinematic emotional"
    
    def generate_np22_lyrics(
        self,
        theme: Optional[str] = None,
        bpm: Optional[int] = None,
        mood: Optional[str] = None
    ) -> str:
        """Generate NP22-style lyrics using OpenAI with the specified template"""
        # Build prompt based on NP22 template
        base_prompt = """Write lyrics in the NP22 sound: a cinematic fusion of soulful rock and modern trap — dark-purple energy, emotional intensity, motivational tone, stadium-level delivery. Focus on clean rhythm, expressive soul, mindset themes. Structure: Hook + Verse 1 + Optional Pre-Hook. Keep flow tight, melodic, empowering."""
        
        if bpm:
            base_prompt += f"\n\nMatch the BPM: {bpm} - ensure the lyrics flow naturally with this tempo."
        
        if mood:
            base_prompt += f"\n\nMood/Energy: {mood}"
        
        if theme:
            base_prompt += f"\n\nTheme: {theme}"
        else:
            base_prompt += "\n\nTheme: general motivational mindset"
        
        # Fallback lyrics
        fallback_lyrics = """[Hook]
Rising up from the darkness, I'm taking control
Every step forward, I'm reaching my goal
This is my moment, this is my time
Nothing can stop me, I'm in my prime

[Verse 1]
Through the struggle and the pain
I found my strength again
No more hiding in the shadows
I'm breaking free from all the chains
Standing tall, I claim my name"""
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured - using fallback lyrics")
            return fallback_lyrics
        
        try:
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional songwriter specializing in NP22-style lyrics: cinematic fusion of soulful rock and modern trap with dark-purple energy, emotional intensity, and motivational tone."},
                    {"role": "user", "content": base_prompt}
                ],
                temperature=0.9
            )
            
            lyrics_text = response.choices[0].message.content.strip() if response.choices[0].message.content else fallback_lyrics
            return lyrics_text
        except Exception as e:
            logger.warning(f"OpenAI lyrics generation failed: {e} - using fallback")
            return fallback_lyrics
    
    def parse_lyrics_to_structured(self, lyrics_text: str) -> Optional[Dict[str, str]]:
        """Parse lyrics text into structured sections based on headers like [Hook], [Verse 1], etc."""
        if not lyrics_text or not isinstance(lyrics_text, str):
            return None
        
        sections = {}
        lines = lyrics_text.split('\n')
        current_section = None
        current_lines = []
        
        for line in lines:
            # Detect section headers: [Hook], [Chorus], [Verse 1], [Verse], [Bridge], etc.
            section_match = re.match(r'^\[(Hook|Chorus|Verse\s*\d*|Bridge|Intro|Outro|Pre-Chorus)\](.*)$', line, re.IGNORECASE)
            
            if section_match:
                # Save previous section
                if current_section and current_lines:
                    section_key = current_section.lower().replace(' ', '').replace('-', '')
                    # Handle verse numbers
                    if 'verse' in section_key:
                        num_match = re.search(r'\d+', current_section)
                        if num_match:
                            section_key = f"verse{num_match.group()}"
                        else:
                            section_key = "verse"
                    sections[section_key] = '\n'.join([l for l in current_lines if l.strip()])
                
                # Start new section
                current_section = section_match.group(1)
                current_lines = []
            elif line.strip():
                current_lines.append(line)
        
        # Save last section
        if current_section and current_lines:
            section_key = current_section.lower().replace(' ', '').replace('-', '')
            if 'verse' in section_key:
                num_match = re.search(r'\d+', current_section)
                if num_match:
                    section_key = f"verse{num_match.group()}"
                else:
                    section_key = "verse"
            sections[section_key] = '\n'.join([l for l in current_lines if l.strip()])
        
        return sections if sections else None
    
    async def write_song(
        self,
        user_id: str,
        session_id: str,
        genre: str,
        mood: str,
        theme: Optional[str] = None,
        beat_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate song lyrics using OpenAI with fallback.
        
        Returns:
            Dict with lyrics, filename, path, project_path, session_id, timestamp
        """
        session_path = get_session_media_path(session_id, user_id)
        
        # Static fallback lyrics
        fallback_lyrics = f"""[Verse 1]
This is a {genre} verse about {mood}
Flowing through the rhythm and the beat
Every word connects with your soul
This is how we make it complete

[Chorus]
{mood.title()} vibes all around
{genre} is the sound we found
Let the music take control
Feel it deep within your soul

[Verse 2]
Building on the energy we share
Taking it higher everywhere
This is more than just a song
This is where we all belong"""
        
        lyrics_text = fallback_lyrics
        provider = "fallback"
        
        # Try OpenAI if key available
        if self.api_key:
            try:
                client = OpenAI(api_key=self.api_key)
                
                beat_context_str = ""
                if beat_context:
                    beat_context_str = f"\nBeat context: {beat_context.get('tempo', 'unknown')} BPM, {beat_context.get('key', 'unknown')} key, {beat_context.get('energy', 'medium')} energy"
                
                prompt = f"""Write song lyrics for a {genre} song with a {mood} mood.
Theme: {theme or 'general'}{beat_context_str}

Provide complete lyrics with verse, chorus, and bridge sections.
Make it authentic and emotionally resonant."""
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional songwriter. Write authentic, emotionally resonant lyrics."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.9
                )
                
                lyrics_text = response.choices[0].message.content.strip() if response.choices[0].message.content else fallback_lyrics
                provider = "openai"
            except Exception as e:
                logger.warning(f"OpenAI lyrics failed: {e} - using fallback")
        
        # Save lyrics.txt
        lyrics_file = session_path / "lyrics.txt"
        with open(lyrics_file, 'w') as f:
            f.write(lyrics_text)
        
        # Parse lyrics into structured sections (verse, chorus, bridge)
        lyrics_lines = lyrics_text.split('\n')
        parsed_lyrics = {"verse": "", "chorus": "", "bridge": ""}
        current_section = None
        
        for line in lyrics_lines:
            line_lower = line.lower().strip()
            if '[verse' in line_lower or line_lower.startswith('verse'):
                current_section = "verse"
                continue
            elif '[chorus' in line_lower or line_lower.startswith('chorus'):
                current_section = "chorus"
                continue
            elif '[bridge' in line_lower or line_lower.startswith('bridge'):
                current_section = "bridge"
                continue
            
            if current_section and line.strip():
                if parsed_lyrics[current_section]:
                    parsed_lyrics[current_section] += "\n" + line.strip()
                else:
                    parsed_lyrics[current_section] = line.strip()
        
        # If no sections found, treat all as verse
        if not any(parsed_lyrics.values()):
            parsed_lyrics["verse"] = lyrics_text
        
        # Note: Voice generation is handled in the router since it uses gtts_speak
        # which is a main.py function. We'll handle it there.
        
        # Update project memory
        memory = await get_or_create_project_memory(session_id, MEDIA_DIR)
        await memory.add_asset("lyrics", f"/media/{user_id}/{session_id}/lyrics.txt", {"genre": genre, "mood": mood})
        await memory.advance_stage("lyrics", "upload")
        
        log_endpoint_event("/songs/write", session_id, "success", {"provider": provider})
        
        return {
            "session_id": session_id,
            "lyrics": lyrics_text,
            "filename": "lyrics.txt",
            "path": str(lyrics_file),
            "project_path": str(session_path),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_lyrics_from_beat(
        self,
        user_id: str,
        session_id: str,
        beat_file_path: Path
    ) -> Dict[str, Any]:
        """
        Generate NP22-style lyrics from uploaded beat file.
        
        Returns:
            Dict with lyrics, filename, path, project_path, session_id, bpm, mood, timestamp
        """
        session_path = get_session_media_path(session_id, user_id)
        
        # Detect BPM and analyze mood
        bpm = self.detect_bpm(beat_file_path)
        mood = self.analyze_mood(beat_file_path)
        
        # Generate lyrics using NP22 template
        lyrics_text = self.generate_np22_lyrics(theme=None, bpm=bpm, mood=mood)
        
        # Prepare paths for saving lyrics
        lyrics_filename = "lyrics.txt"
        lyrics_path = session_path / lyrics_filename
        project_path = session_path
        
        # Write lyrics to disk
        with open(lyrics_path, "w", encoding="utf-8") as f:
            f.write(lyrics_text)
        
        # Update project memory
        project_file = session_path / "project.json"
        if project_file.exists():
            with open(project_file, "r", encoding="utf-8") as f:
                project = json.load(f)
        else:
            project = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "assets": {}
            }
        
        if project:
            project["lyrics"] = str(lyrics_path)
            project["lyrics_text"] = lyrics_text
            project["updated_at"] = datetime.now().isoformat()
            with open(project_file, "w", encoding="utf-8") as f:
                json.dump(project, f, indent=2)
        
        # Auto-save to orchestrator
        orchestrator = ProjectOrchestrator(user_id, session_id)
        orchestrator.update_stage("lyrics", {
            "text": lyrics_text,
            "meta": {},
            "completed": True
        })
        
        log_endpoint_event("/lyrics/from_beat", session_id, "success", {"bpm": bpm, "mood": mood})
        
        return {
            "session_id": session_id,
            "lyrics": lyrics_text,
            "filename": lyrics_filename,
            "path": str(lyrics_path),
            "project_path": str(project_path),
            "bpm": bpm,
            "mood": mood,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def generate_free_lyrics(self, theme: str) -> Dict[str, Any]:
        """
        Generate NP22-style lyrics from theme only.
        
        Returns:
            Dict with lyrics
        """
        lyrics_text = self.generate_np22_lyrics(theme=theme, bpm=None, mood=None)
        
        log_endpoint_event("/lyrics/free", None, "success", {"theme": theme})
        
        return {"lyrics": lyrics_text}
    
    async def refine_lyrics(
        self,
        lyrics: str,
        instruction: str,
        bpm: Optional[int] = None,
        history: Optional[List[dict]] = None,
        structured_lyrics: Optional[Dict[str, str]] = None,
        rhythm_map: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Refine, rewrite, or extend lyrics based on user instructions.
        
        Returns:
            Dict with refined lyrics
        """
        # Parse structured lyrics if not provided
        if not structured_lyrics:
            structured_lyrics = self.parse_lyrics_to_structured(lyrics)
        
        # Build prompt using NP22 template + original lyrics + user instruction + BPM if given
        base_prompt = """You are an NP22-style lyric collaborator. Rewrite lyrics based on instruction while keeping:
- NP22 style (cinematic soulful rock × modern trap)
- dark-purple energy
- mindset themes
- melodic flow
- stadium-level emotion

Only modify what the instruction asks for. Keep original structure unless instruction says otherwise."""
        
        if bpm:
            base_prompt += f"\n\nBPM: {bpm} - ensure the lyrics flow naturally with this tempo."
        
        # Add structured lyric information to prompt
        structure_info = ""
        if structured_lyrics:
            structure_info = "\n\nOriginal lyric structure:\n"
            for section_key, section_text in structured_lyrics.items():
                line_count = len([l for l in section_text.split('\n') if l.strip()])
                structure_info += f"- {section_key.capitalize()}: {line_count} lines\n"
        
        # Add rhythm map information
        rhythm_info = ""
        if rhythm_map:
            rhythm_info = "\n\nRhythm map of lines (approximate bars per line):\n"
            for section_key, bar_counts in rhythm_map.items():
                if isinstance(bar_counts, list):
                    rhythm_info += f"{section_key.capitalize()} bars: {bar_counts}\n"
            rhythm_info += "Please preserve approximate rhythm when refining.\n"
        
        # Add conversation history context
        history_context = ""
        if history and len(history) > 0:
            history_context = "\n\nHere is recent conversation context:\n"
            for i, entry in enumerate(history, 1):
                prev_lyrics_preview = entry.get('previousLyrics', '')[:100] + '...' if len(entry.get('previousLyrics', '')) > 100 else entry.get('previousLyrics', '')
                instruction = entry.get('instruction', '')
                history_context += f"{i}. User said: {instruction}\n"
                history_context += f"   Previous lyrics: {prev_lyrics_preview}\n"
        
        user_prompt = f"""Original lyrics:
{lyrics}{structure_info}{rhythm_info}{history_context}

User instruction: {instruction}

Rewrite the lyrics according to the instruction while maintaining NP22 style. Return only the revised lyrics as plain text (no JSON, no explanations)."""
        
        # Fallback: simple instruction-applied version
        fallback_lyrics = lyrics  # Keep original if refinement fails
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured - returning original lyrics")
            log_endpoint_event("/lyrics/refine", None, "error", {"error": "OpenAI API key not configured"})
            return {"lyrics": fallback_lyrics}
        
        try:
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": base_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9
            )
            
            refined_lyrics = response.choices[0].message.content.strip() if response.choices[0].message.content else fallback_lyrics
            
            log_endpoint_event("/lyrics/refine", None, "success", {"instruction_length": len(instruction), "bpm": bpm})
            return {"lyrics": refined_lyrics}
        except Exception as e:
            logger.warning(f"OpenAI lyrics refinement failed: {e} - returning original lyrics")
            log_endpoint_event("/lyrics/refine", None, "error", {"error": str(e)})
            raise Exception(f"Failed to refine lyrics: {str(e)}")

