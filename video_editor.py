"""
AI Video Editor with Beat-Sync
Handles video editing, beat detection, and automatic cut synchronization for music videos.
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class VideoEditor:
    """
    AI-powered video editor with beat-synchronization for music videos.
    Uses librosa for beat detection and ffmpeg for video processing.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.clips_dir = f"sessions/{session_id}/video_clips"
        self.output_dir = f"sessions/{session_id}/video_output"
        os.makedirs(self.clips_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
    def detect_beats(self, audio_path: str) -> Dict:
        """
        Detect beats in audio using librosa.
        Returns beat times and tempo for video synchronization.
        """
        try:
            import librosa
            import numpy as np
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050)
            
            # Detect tempo and beats
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            
            # Extract additional rhythmic features
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            
            return {
                "success": True,
                "tempo": float(tempo),
                "beat_count": len(beat_times),
                "beat_times": beat_times.tolist(),
                "onset_times": onset_times.tolist(),
                "duration": float(librosa.get_duration(y=y, sr=sr)),
                "analysis": {
                    "avg_beat_interval": float(np.mean(np.diff(beat_times))) if len(beat_times) > 1 else 0,
                    "rhythm_consistency": float(np.std(np.diff(beat_times))) if len(beat_times) > 1 else 0
                }
            }
            
        except ImportError:
            return {
                "success": False,
                "error": "librosa_not_available",
                "tempo": 120.0,
                "beat_count": 0,
                "beat_times": [],
                "onset_times": [],
                "message": "librosa not available, using manual beat markers"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tempo": 120.0,
                "beat_count": 0,
                "beat_times": [],
                "onset_times": []
            }
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        Get video metadata using ffprobe.
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Extract video stream info
                video_stream = next(
                    (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
                    {}
                )
                
                return {
                    "success": True,
                    "duration": float(data.get('format', {}).get('duration', 0)),
                    "width": int(video_stream.get('width', 0)),
                    "height": int(video_stream.get('height', 0)),
                    "fps": eval(video_stream.get('r_frame_rate', '30/1')),
                    "codec": video_stream.get('codec_name', 'unknown')
                }
            else:
                return {"success": False, "error": "ffprobe_failed"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_beat_sync_edit(
        self,
        clips: List[Dict],
        beat_times: List[float],
        audio_path: str,
        output_name: str = "beat_sync_video.mp4"
    ) -> Dict:
        """
        Create a beat-synchronized video edit by cutting clips at beat markers.
        
        Args:
            clips: List of clip dicts with {path, start_time, duration}
            beat_times: List of beat timestamps from audio analysis
            audio_path: Path to the audio track
            output_name: Name for output video file
            
        Returns:
            Dict with success status and output path
        """
        try:
            if not beat_times:
                return {
                    "success": False,
                    "error": "no_beats",
                    "message": "No beat times provided for synchronization"
                }
            
            # Create concat file for ffmpeg
            concat_file = os.path.join(self.output_dir, "concat_list.txt")
            temp_clips = []
            
            # Cut clips to align with beats
            for i, clip in enumerate(clips):
                if i >= len(beat_times) - 1:
                    break
                    
                clip_path = clip.get('path', '')
                if not os.path.exists(clip_path):
                    continue
                
                # Calculate clip duration based on beat intervals
                start_beat = beat_times[i]
                end_beat = beat_times[i + 1]
                duration = end_beat - start_beat
                
                # Cut clip to beat duration
                temp_clip = os.path.join(self.output_dir, f"temp_clip_{i}.mp4")
                cut_cmd = [
                    'ffmpeg',
                    '-i', clip_path,
                    '-ss', str(clip.get('start_time', 0)),
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-y',
                    temp_clip
                ]
                
                result = subprocess.run(cut_cmd, capture_output=True)
                if result.returncode == 0:
                    temp_clips.append(temp_clip)
            
            if not temp_clips:
                return {
                    "success": False,
                    "error": "no_clips_processed",
                    "message": "No clips could be processed"
                }
            
            # Write concat list
            with open(concat_file, 'w') as f:
                for clip in temp_clips:
                    f.write(f"file '{clip}'\n")
            
            # Concatenate clips
            concat_output = os.path.join(self.output_dir, "video_only.mp4")
            concat_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                concat_output
            ]
            
            subprocess.run(concat_cmd, capture_output=True)
            
            # Merge with audio
            output_path = os.path.join(self.output_dir, output_name)
            merge_cmd = [
                'ffmpeg',
                '-i', concat_output,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                '-y',
                output_path
            ]
            
            result = subprocess.run(merge_cmd, capture_output=True)
            
            # Cleanup temp files
            for clip in temp_clips:
                if os.path.exists(clip):
                    os.remove(clip)
            if os.path.exists(concat_file):
                os.remove(concat_file)
            if os.path.exists(concat_output):
                os.remove(concat_output)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output_path": output_path,
                    "clip_count": len(temp_clips),
                    "message": f"Beat-synced video created with {len(temp_clips)} clips"
                }
            else:
                return {
                    "success": False,
                    "error": "merge_failed",
                    "message": "Failed to merge video with audio"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Beat-sync edit failed: {str(e)}"
            }
    
    def auto_edit_to_beat(
        self,
        video_clips: List[str],
        audio_path: str,
        style: str = "energetic"
    ) -> Dict:
        """
        Automatically edit video clips to match audio beats.
        
        Args:
            video_clips: List of video file paths
            audio_path: Path to audio track
            style: Editing style (energetic, smooth, dramatic)
            
        Returns:
            Result dict with AI suggestions and beat-sync data
        """
        # Detect beats in audio
        beat_data = self.detect_beats(audio_path)
        
        if not beat_data.get("success"):
            return {
                "success": False,
                "error": "beat_detection_failed",
                "message": "Could not detect beats in audio",
                "suggestions": {
                    "fallback": "Manual beat markers recommended",
                    "alternative": "Try uploading audio with clearer rhythm"
                }
            }
        
        # Analyze clips
        clip_info = []
        for clip_path in video_clips:
            info = self.get_video_info(clip_path)
            if info.get("success"):
                clip_info.append({
                    "path": clip_path,
                    "duration": info["duration"],
                    "resolution": f"{info['width']}x{info['height']}"
                })
        
        # Generate AI editing suggestions
        tempo = beat_data["tempo"]
        beat_count = beat_data["beat_count"]
        beat_times = beat_data["beat_times"]
        
        suggestions = self._generate_edit_suggestions(
            tempo, beat_count, len(clip_info), style
        )
        
        return {
            "success": True,
            "beat_data": beat_data,
            "clip_info": clip_info,
            "suggestions": suggestions,
            "total_clips": len(clip_info),
            "total_beats": beat_count,
            "message": f"Detected {beat_count} beats at {tempo:.1f} BPM"
        }
    
    def _generate_edit_suggestions(
        self,
        tempo: float,
        beat_count: int,
        clip_count: int,
        style: str
    ) -> Dict:
        """
        Generate AI editing suggestions based on tempo and style.
        """
        # Determine cut frequency based on tempo and style
        if style == "energetic":
            cuts_per_clip = 4 if tempo > 120 else 2
            transition = "quick cuts"
        elif style == "smooth":
            cuts_per_clip = 1
            transition = "crossfades"
        else:  # dramatic
            cuts_per_clip = 2
            transition = "slow motion and quick cuts"
        
        return {
            "recommended_cuts": cuts_per_clip * clip_count,
            "cut_style": transition,
            "pacing": "fast" if tempo > 120 else "moderate" if tempo > 90 else "slow",
            "tips": [
                f"Cut on every {'other ' if cuts_per_clip == 2 else ''}beat for {style} feel",
                f"Use {transition} for visual flow",
                "Match action peaks to beat hits",
                "Consider slow-motion for dramatic moments"
            ],
            "ai_insights": {
                "tempo_category": "high-energy" if tempo > 120 else "mid-tempo" if tempo > 90 else "laid-back",
                "suggested_clip_length": f"{60/tempo:.2f}s per cut" if tempo > 0 else "N/A",
                "total_clips_needed": max(clip_count, beat_count // cuts_per_clip)
            }
        }
    
    def export_video(
        self,
        video_path: str,
        format: str = "mp4",
        quality: str = "high",
        resolution: Optional[str] = None
    ) -> Dict:
        """
        Export video with specified settings.
        
        Args:
            video_path: Path to source video
            format: Output format (mp4, mov, avi)
            quality: Quality preset (high, medium, low)
            resolution: Optional resolution (e.g., "1920x1080")
            
        Returns:
            Export result with output path
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"export_{timestamp}.{format}"
            output_path = os.path.join(self.output_dir, output_name)
            
            # Build ffmpeg command
            cmd = ['ffmpeg', '-i', video_path]
            
            # Quality settings
            if quality == "high":
                cmd.extend(['-c:v', 'libx264', '-preset', 'slow', '-crf', '18'])
            elif quality == "medium":
                cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '23'])
            else:  # low
                cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '28'])
            
            # Resolution
            if resolution:
                cmd.extend(['-s', resolution])
            
            # Audio codec
            cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
            
            # Output
            cmd.extend(['-y', output_path])
            
            result = subprocess.run(cmd, capture_output=True)
            
            if result.returncode == 0:
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                return {
                    "success": True,
                    "output_path": output_path,
                    "file_size_mb": round(file_size, 2),
                    "format": format,
                    "quality": quality,
                    "message": "Video exported successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "export_failed",
                    "message": result.stderr.decode()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Export failed: {str(e)}"
            }
