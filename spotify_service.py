"""
Spotify Web API Integration for Label-in-a-Box v4
Track analysis: key, BPM, energy, danceability using Spotify Web API
Graceful fallback to librosa for local analysis
"""

import os
import logging
import base64
from typing import Dict, Optional
import requests
import librosa
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class SpotifyAnalysisService:
    """
    Analyze audio tracks using Spotify Web API (Client Credentials flow).
    Falls back to librosa for local analysis when Spotify keys unavailable.
    """
    
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.access_token = None
        self.spotify_available = bool(self.client_id and self.client_secret)
        
        if not self.spotify_available:
            logger.warning("Spotify API keys not set - using librosa fallback for audio analysis")
    
    def _get_access_token(self) -> Optional[str]:
        """
        Get Spotify access token using Client Credentials flow.
        Free tier - no user authentication required.
        """
        if not self.spotify_available:
            return None
        
        try:
            # Encode credentials
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_str.encode('utf-8')
            auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
            
            # Request token
            url = "https://accounts.spotify.com/api/token"
            headers = {
                "Authorization": f"Basic {auth_base64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {"grant_type": "client_credentials"}
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            
            logger.info("Spotify access token obtained successfully")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get Spotify access token: {e}")
            return None
    
    def analyze_track_by_uri(self, spotify_uri: str) -> Dict:
        """
        Analyze a Spotify track by URI (e.g., spotify:track:3n3Ppam7vgaVa1iaRUc9Lp).
        Returns audio features: key, tempo, energy, danceability, etc.
        """
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            return {
                "status": "error",
                "message": "Spotify API unavailable - use local analysis instead"
            }
        
        try:
            # Extract track ID from URI
            track_id = spotify_uri.split(':')[-1]
            
            # Get audio features
            url = f"https://api.spotify.com/v1/audio-features/{track_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            features = response.json()
            
            # Map key number to musical key
            key_map = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            mode_map = {0: 'Minor', 1: 'Major'}
            
            return {
                "status": "ready",
                "source": "spotify",
                "key": f"{key_map[features['key']]} {mode_map[features['mode']]}",
                "key_number": features['key'],
                "mode": features['mode'],
                "tempo": round(features['tempo'], 1),
                "energy": round(features['energy'], 3),
                "danceability": round(features['danceability'], 3),
                "valence": round(features['valence'], 3),
                "acousticness": round(features['acousticness'], 3),
                "instrumentalness": round(features['instrumentalness'], 3),
                "liveness": round(features['liveness'], 3),
                "speechiness": round(features['speechiness'], 3),
                "loudness": round(features['loudness'], 2),
                "time_signature": features['time_signature']
            }
            
        except Exception as e:
            logger.error(f"Spotify track analysis failed: {e}")
            return {
                "status": "error",
                "message": f"Spotify analysis failed: {str(e)}"
            }
    
    def search_track(self, query: str, artist: Optional[str] = None) -> Optional[str]:
        """
        Search for a track on Spotify and return its URI.
        Useful for finding reference tracks.
        """
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            logger.warning("Spotify search unavailable - no access token")
            return None
        
        try:
            # Build search query
            search_query = f"track:{query}"
            if artist:
                search_query += f" artist:{artist}"
            
            url = "https://api.spotify.com/v1/search"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            params = {
                "q": search_query,
                "type": "track",
                "limit": 1
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data["tracks"]["items"]:
                track = data["tracks"]["items"][0]
                return track["uri"]
            else:
                logger.warning(f"No Spotify tracks found for: {query}")
                return None
                
        except Exception as e:
            logger.error(f"Spotify search failed: {e}")
            return None
    
    def analyze_local_file(self, audio_path: Path) -> Dict:
        """
        Fallback: Analyze local audio file using librosa.
        Free and offline-capable.
        """
        try:
            logger.info(f"Analyzing local file with librosa: {audio_path}")
            
            # Load audio file
            y, sr = librosa.load(str(audio_path), sr=None, duration=60)  # Analyze first 60 seconds
            
            # Estimate tempo (BPM)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            # Estimate key using chromagram
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            key_number = int(np.argmax(chroma_mean))
            
            # Estimate energy (RMS)
            rms = librosa.feature.rms(y=y)
            energy = float(np.mean(rms))
            
            # Normalize energy to 0-1 scale (rough approximation)
            energy_normalized = min(energy * 2, 1.0)
            
            # Estimate spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            brightness = float(np.mean(spectral_centroid) / 4000)  # Normalize
            
            # Zero-crossing rate (measure of noisiness)
            zcr = librosa.feature.zero_crossing_rate(y)
            noisiness = float(np.mean(zcr))
            
            # Map key number to musical key
            key_map = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            
            return {
                "status": "ready",
                "source": "librosa",
                "key": f"{key_map[key_number]} (estimated)",
                "key_number": key_number,
                "tempo": round(float(tempo), 1),
                "energy": round(energy_normalized, 3),
                "brightness": round(brightness, 3),
                "noisiness": round(noisiness, 3),
                "note": "Analysis performed locally with librosa (Spotify API unavailable)"
            }
            
        except Exception as e:
            logger.error(f"Librosa analysis failed: {e}")
            return {
                "status": "error",
                "message": f"Local analysis failed: {str(e)}"
            }
    
    def analyze_reference_track(
        self,
        track_title: Optional[str] = None,
        artist: Optional[str] = None,
        local_file: Optional[Path] = None
    ) -> Dict:
        """
        Unified analysis method: tries Spotify first, falls back to librosa.
        
        Args:
            track_title: Track name to search on Spotify
            artist: Artist name for better search results
            local_file: Path to local audio file for fallback analysis
            
        Returns:
            Dict with audio features and analysis source
        """
        # Try Spotify first if track info provided
        if track_title and self.spotify_available:
            spotify_uri = self.search_track(track_title, artist)
            if spotify_uri:
                result = self.analyze_track_by_uri(spotify_uri)
                if result.get("status") == "ready":
                    return result
        
        # Fallback to local analysis if file provided
        if local_file and local_file.exists():
            return self.analyze_local_file(local_file)
        
        # No analysis possible
        return {
            "status": "error",
            "message": "Unable to analyze track - provide Spotify credentials or local audio file"
        }


def get_spotify_service() -> SpotifyAnalysisService:
    """Factory function to get Spotify service."""
    return SpotifyAnalysisService()
