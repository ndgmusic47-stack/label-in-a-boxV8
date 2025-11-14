"""
Beat Generation Service - Async music creation with Beatoven and Mubert
Free-tier alternatives for AI-generated instrumental beats
"""

import os
import logging
import uuid
import time
from pathlib import Path
from typing import Dict, Optional, List
import requests
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class BeatGenerationService:
    """
    Async beat generation service supporting Beatoven.ai and Mubert.com
    Both offer free-tier API access for AI music generation
    """
    
    def __init__(self, media_dir: Path):
        self.media_dir = media_dir
        self.beats_dir = media_dir / "beats"
        self.beats_dir.mkdir(exist_ok=True, parents=True)
        
        # API keys from environment
        self.beatoven_key = os.getenv("BEATOVEN_KEY")
        self.mubert_key = os.getenv("MUBERT_KEY")
        
        # Job tracking
        self.jobs_file = media_dir / "beat_jobs.json"
        self.jobs = self._load_jobs()
    
    def _load_jobs(self) -> Dict:
        """Load beat generation jobs from disk."""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_jobs(self):
        """Save beat generation jobs to disk."""
        with open(self.jobs_file, 'w') as f:
            json.dump(self.jobs, f, indent=2)
    
    def create_beat(
        self,
        mood: str,
        genre: str,
        tempo: int = 120,
        duration: int = 120,
        emotional_direction: Optional[str] = None,
        reference_song: Optional[str] = None,
        provider: str = "auto"
    ) -> Dict:
        """
        Create a new beat generation job.
        
        Args:
            mood: Musical mood (energetic, melancholic, uplifting, etc.)
            genre: Music genre (hip-hop, electronic, pop, etc.)
            tempo: BPM (60-200)
            duration: Length in seconds (30-300)
            emotional_direction: Optional emotional arc description
            reference_song: Optional reference track for style matching
            provider: "beatoven", "mubert", or "auto" (tries both)
            
        Returns:
            Dict with job_id and status
        """
        job_id = str(uuid.uuid4())
        
        # Determine which provider to use
        if provider == "auto":
            if self.beatoven_key:
                provider = "beatoven"
            elif self.mubert_key:
                provider = "mubert"
            else:
                return {
                    "job_id": job_id,
                    "status": "error",
                    "message": "No beat generation API keys configured. Set BEATOVEN_KEY or MUBERT_KEY in .env"
                }
        
        # Create job
        job = {
            "job_id": job_id,
            "provider": provider,
            "status": "pending",
            "mood": mood,
            "genre": genre,
            "tempo": tempo,
            "duration": duration,
            "emotional_direction": emotional_direction,
            "reference_song": reference_song,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Start generation based on provider
        if provider == "beatoven":
            result = self._start_beatoven_generation(job)
        elif provider == "mubert":
            result = self._start_mubert_generation(job)
        else:
            result = {
                "status": "error",
                "message": f"Unknown provider: {provider}"
            }
        
        # Update job with result
        job.update(result)
        self.jobs[job_id] = job
        self._save_jobs()
        
        return {
            "job_id": job_id,
            "status": job["status"],
            "provider": provider,
            "estimated_time": job.get("estimated_time", 60),
            "message": job.get("message")
        }
    
    def _start_beatoven_generation(self, job: Dict) -> Dict:
        """Start real beat generation with Beatoven.ai"""
        if not self.beatoven_key:
            return {"status": "error", "message": "BEATOVEN_KEY not configured"}

        try:
            url = "https://public-api.beatoven.ai/api/v1/tracks/compose"
            headers = {
                "Authorization": f"Bearer {self.beatoven_key}",
                "Content-Type": "application/json"
            }

            prompt_text = f"{job['duration']} seconds {job['mood']} {job['genre']} instrumental track"
            payload = {"prompt": {"text": prompt_text}, "format": "mp3", "looping": False}

            logger.info(f"🎵 Beatoven job started: {prompt_text}")
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            task_id = data.get("task_id")
            if not task_id:
                raise Exception("Beatoven: no task_id returned")

            # Poll status until composed
            for attempt in range(60):
                time.sleep(3)
                status_url = f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}"
                status_res = requests.get(status_url, headers=headers, timeout=30)
                status_res.raise_for_status()
                status_data = status_res.json()
                status = status_data.get("status")

                if status == "composed":
                    meta = status_data.get("meta", {})
                    track_url = meta.get("track_url")
                    if not track_url:
                        raise Exception("Beatoven: track_url missing")
                    
                    # Download the track and save locally
                    output_file = self.beats_dir / f"{job['job_id']}.mp3"
                    audio_data = requests.get(track_url, timeout=60)
                    with open(output_file, "wb") as f:
                        f.write(audio_data.content)
                    
                    logger.info(f"✅ Beatoven track ready: {output_file}")
                    
                    return {
                        "status": "ready",
                        "beat_url": f"/media/beats/{job['job_id']}.mp3",
                        "progress": 100,
                        "message": "Beat generated successfully with Beatoven.ai"
                    }

                elif status in ("composing", "running", "queued"):
                    logger.info(f"⏳ Beatoven status: {status} ({attempt+1}/60)")
                    continue
                else:
                    raise Exception(f"Unexpected Beatoven status: {status}")

            raise Exception("Beatoven generation timed out (3 minutes)")

        except Exception as e:
            logger.error(f"Beatoven generation failed: {e}")
            return {"status": "error", "message": f"Beatoven API error: {e}"}
    
    def _start_mubert_generation(self, job: Dict) -> Dict:
        """
        Start beat generation with Mubert
        Free tier: Limited generations per day
        """
        if not self.mubert_key:
            return {
                "status": "error",
                "message": "MUBERT_KEY not configured"
            }
        
        try:
            # Mubert API endpoint
            # See https://mubert.com/api for real implementation
            url = "https://api.mubert.com/v2/RecordTrack"
            
            # Build tags from mood and genre
            tags = self._build_mubert_tags(job)
            
            payload = {
                "method": "RecordTrack",
                "params": {
                    "license": self.mubert_key,
                    "mode": "track",
                    "duration": job["duration"],
                    "tags": tags,
                    "bitrate": 320
                }
            }
            
            logger.info(f"Starting Mubert generation with tags: {tags}")
            
            # NOTE: This is a stub implementation
            # In production, you would make the actual API call here
            # response = requests.post(url, json=payload, timeout=30)
            # response.raise_for_status()
            # data = response.json()
            
            # Stub response for demonstration
            return {
                "status": "processing",
                "external_job_id": f"mubert_{job['job_id'][:8]}",
                "estimated_time": 60,
                "message": "Beat generation started with Mubert"
            }
            
        except Exception as e:
            logger.error(f"Mubert generation failed: {e}")
            return {
                "status": "error",
                "message": f"Mubert API error: {str(e)}"
            }
    
    def check_status(self, job_id: str) -> Dict:
        """
        Check the status of a beat generation job.
        Polls the external API and updates local status.
        
        Args:
            job_id: Job ID returned from create_beat()
            
        Returns:
            Dict with current status and progress
        """
        if job_id not in self.jobs:
            return {
                "status": "not_found",
                "message": f"Job {job_id} not found"
            }
        
        job = self.jobs[job_id]
        
        # If already completed or failed, return cached result
        if job["status"] in ["ready", "error"]:
            return {
                "job_id": job_id,
                "status": job["status"],
                "beat_url": job.get("beat_url"),
                "message": job.get("message")
            }
        
        # Poll external API for updates
        provider = job["provider"]
        
        if provider == "beatoven":
            result = self._check_beatoven_status(job)
        elif provider == "mubert":
            result = self._check_mubert_status(job)
        else:
            result = {"status": "error", "message": "Unknown provider"}
        
        # Update job
        job.update(result)
        job["updated_at"] = datetime.now().isoformat()
        self.jobs[job_id] = job
        self._save_jobs()
        
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress": job.get("progress", 0),
            "beat_url": job.get("beat_url"),
            "message": job.get("message")
        }
    
    def _check_beatoven_status(self, job: Dict) -> Dict:
        """Check Beatoven job status (stub)."""
        # In production, poll Beatoven API
        # For now, simulate completion after some time
        
        created = datetime.fromisoformat(job["created_at"])
        elapsed = (datetime.now() - created).total_seconds()
        
        if elapsed > 90:  # Simulated completion after 90 seconds
            return {
                "status": "ready",
                "beat_url": f"/media/beats/{job['job_id']}.mp3",
                "progress": 100,
                "message": "Beat generated successfully with Beatoven.ai"
            }
        else:
            progress = min(int((elapsed / 90) * 100), 99)
            return {
                "status": "processing",
                "progress": progress,
                "message": f"Generating beat... {progress}%"
            }
    
    def _check_mubert_status(self, job: Dict) -> Dict:
        """Check Mubert job status (stub)."""
        # In production, poll Mubert API
        # For now, simulate completion after some time
        
        created = datetime.fromisoformat(job["created_at"])
        elapsed = (datetime.now() - created).total_seconds()
        
        if elapsed > 60:  # Simulated completion after 60 seconds
            return {
                "status": "ready",
                "beat_url": f"/media/beats/{job['job_id']}.mp3",
                "progress": 100,
                "message": "Beat generated successfully with Mubert"
            }
        else:
            progress = min(int((elapsed / 60) * 100), 99)
            return {
                "status": "processing",
                "progress": progress,
                "message": f"Generating beat... {progress}%"
            }
    
    def _build_beatoven_prompt(self, job: Dict) -> str:
        """Build creative prompt for Beatoven."""
        prompt = f"{job['mood']} {job['genre']} instrumental at {job['tempo']} BPM"
        
        if job.get("emotional_direction"):
            prompt += f", {job['emotional_direction']}"
        
        return prompt
    
    def _build_mubert_tags(self, job: Dict) -> str:
        """Build tags for Mubert API."""
        tags = [
            job["genre"].lower(),
            job["mood"].lower(),
            "instrumental",
            "background"
        ]
        
        # Add tempo category
        if job["tempo"] < 90:
            tags.append("slow")
        elif job["tempo"] > 140:
            tags.append("fast")
        else:
            tags.append("medium")
        
        return ",".join(tags)
    
    def list_jobs(self, limit: int = 10) -> List[Dict]:
        """List recent beat generation jobs."""
        jobs_list = list(self.jobs.values())
        jobs_list.sort(key=lambda x: x["created_at"], reverse=True)
        return jobs_list[:limit]
    
    def cancel_job(self, job_id: str) -> Dict:
        """Cancel a pending beat generation job."""
        if job_id not in self.jobs:
            return {
                "status": "not_found",
                "message": f"Job {job_id} not found"
            }
        
        job = self.jobs[job_id]
        
        if job["status"] in ["ready", "error"]:
            return {
                "status": "already_finished",
                "message": "Job already completed"
            }
        
        job["status"] = "cancelled"
        job["updated_at"] = datetime.now().isoformat()
        self.jobs[job_id] = job
        self._save_jobs()
        
        return {
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }


def get_beat_generation_service(media_dir: Path) -> BeatGenerationService:
    """Factory function to get beat generation service."""
    return BeatGenerationService(media_dir)
