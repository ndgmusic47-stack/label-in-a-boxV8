"""
Reference & Influence Engine for Label-in-a-Box v4
Analyzes reference tracks using librosa and Spotify API
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional
import librosa
import numpy as np

logger = logging.getLogger(__name__)

class ReferenceAnalyzer:
    """
    Analyzes audio files to extract musical features
    Uses librosa for local analysis and Spotify API for URL-based tracks
    """
    
    def __init__(self):
        self.spotify_client = None
        if os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET"):
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials
                
                auth_manager = SpotifyClientCredentials(
                    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
                )
                self.spotify_client = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("Spotify API client initialized")
            except Exception as e:
                logger.warning(f"Spotify API init failed: {e}")
    
    def analyze_local_file(self, file_path: Path) -> Dict:
        """
        Analyze a local audio file using librosa
        """
        try:
            logger.info(f"Analyzing {file_path}...")
            
            # Load audio
            y, sr = librosa.load(str(file_path), duration=60)  # Analyze first 60s
            
            # Tempo and beat analysis
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            # Key detection (simplified chromagram analysis)
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            key_idx = np.argmax(np.sum(chroma, axis=1))
            keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            estimated_key = keys[key_idx]
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
            
            # RMS energy (for loudness approximation)
            rms = librosa.feature.rms(y=y)
            
            # Zero crossing rate (for percussiveness)
            zcr = librosa.feature.zero_crossing_rate(y)
            
            analysis = {
                "bpm": float(tempo),
                "key": estimated_key,
                "duration_sec": float(len(y) / sr),
                "energy": float(np.mean(rms)),
                "spectral_centroid": float(np.mean(spectral_centroids)),
                "spectral_rolloff": float(np.mean(spectral_rolloff)),
                "zero_crossing_rate": float(np.mean(zcr)),
                "brightness": "high" if np.mean(spectral_centroids) > 3000 else "medium" if np.mean(spectral_centroids) > 1500 else "low",
                "percussiveness": "high" if np.mean(zcr) > 0.1 else "medium" if np.mean(zcr) > 0.05 else "low",
                "provider": "librosa"
            }
            
            logger.info(f"Analysis complete: {analysis['bpm']} BPM in {analysis['key']}")
            return analysis
            
        except Exception as e:
            logger.error(f"Librosa analysis failed: {e}")
            return {
                "error": str(e),
                "provider": "librosa_error"
            }
    
    def analyze_spotify_url(self, spotify_url: str) -> Dict:
        """
        Analyze a Spotify track URL using Spotify Audio Features API
        """
        if not self.spotify_client:
            return {
                "error": "Spotify API not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET",
                "provider": "spotify_unavailable"
            }
        
        try:
            # Extract track ID from URL
            track_id = spotify_url.split("/")[-1].split("?")[0]
            
            # Get audio features
            features = self.spotify_client.audio_features(track_id)[0]
            track_info = self.spotify_client.track(track_id)
            
            # Map Spotify key integers to note names
            keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key_name = keys[features['key']] if features['key'] >= 0 else "Unknown"
            mode = "Major" if features['mode'] == 1 else "Minor"
            
            analysis = {
                "bpm": features['tempo'],
                "key": f"{key_name} {mode}",
                "energy": features['energy'],
                "valence": features['valence'],  # Happiness/positivity
                "danceability": features['danceability'],
                "loudness": features['loudness'],
                "speechiness": features['speechiness'],
                "instrumentalness": features['instrumentalness'],
                "acousticness": features['acousticness'],
                "duration_sec": features['duration_ms'] / 1000,
                "track_name": track_info['name'],
                "artist": track_info['artists'][0]['name'],
                "mood": self._interpret_mood(features),
                "provider": "spotify"
            }
            
            logger.info(f"Spotify analysis: {analysis['track_name']} by {analysis['artist']}")
            return analysis
            
        except Exception as e:
            logger.error(f"Spotify analysis failed: {e}")
            return {
                "error": str(e),
                "provider": "spotify_error"
            }
    
    def _interpret_mood(self, features: Dict) -> str:
        """
        Interpret Spotify features into a mood description
        """
        energy = features['energy']
        valence = features['valence']
        
        if energy > 0.7 and valence > 0.6:
            return "energetic and positive"
        elif energy > 0.7 and valence < 0.4:
            return "intense and aggressive"
        elif energy < 0.4 and valence > 0.6:
            return "calm and uplifting"
        elif energy < 0.4 and valence < 0.4:
            return "melancholic and introspective"
        elif valence > 0.6:
            return "upbeat and cheerful"
        elif valence < 0.4:
            return "dark and moody"
        else:
            return "balanced and neutral"
    
    def get_production_suggestions(self, analysis: Dict) -> Dict:
        """
        Generate production suggestions based on analysis
        """
        suggestions = {
            "recommended_bpm": int(analysis.get("bpm", 120)),
            "recommended_key": analysis.get("key", "C Major"),
            "mood_keywords": [],
            "production_tips": []
        }
        
        # BPM-based suggestions
        bpm = analysis.get("bpm", 120)
        if bpm < 80:
            suggestions["mood_keywords"].extend(["slow", "emotional", "ballad"])
            suggestions["production_tips"].append("Consider lush pads and reverb for atmosphere")
        elif bpm < 100:
            suggestions["mood_keywords"].extend(["mid-tempo", "groovy", "chill"])
            suggestions["production_tips"].append("Focus on groove and pocket in the rhythm")
        elif bpm < 130:
            suggestions["mood_keywords"].extend(["energetic", "upbeat", "pop"])
            suggestions["production_tips"].append("Tight drums and catchy melodies work well")
        else:
            suggestions["mood_keywords"].extend(["fast", "intense", "electronic"])
            suggestions["production_tips"].append("High-energy synths and compressed drums")
        
        # Energy-based suggestions
        energy = analysis.get("energy", 0.5)
        if energy > 0.7:
            suggestions["production_tips"].append("Maintain high energy with layered elements")
        elif energy < 0.3:
            suggestions["production_tips"].append("Keep arrangement sparse and intimate")
        
        return suggestions

def analyze_reference(file_path: Optional[Path] = None, spotify_url: Optional[str] = None) -> Dict:
    """
    Factory function to analyze a reference track
    """
    analyzer = ReferenceAnalyzer()
    
    if file_path:
        return analyzer.analyze_local_file(file_path)
    elif spotify_url:
        return analyzer.analyze_spotify_url(spotify_url)
    else:
        return {"error": "No file or URL provided"}
