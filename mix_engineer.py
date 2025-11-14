"""
AI Mix Engineer for Label-in-a-Box v4
Intelligent mixing suggestions and auto-mix features
"""

import librosa
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AIMixEngineer:
    """
    AI-powered mix engineer that analyzes tracks and provides mixing suggestions.
    Uses audio analysis to determine optimal mixing parameters.
    """
    
    def __init__(self):
        self.suggested_params = {}
    
    def analyze_track(self, audio_path: str) -> Dict:
        """Analyze a single audio track for mixing characteristics"""
        try:
            y, sr = librosa.load(audio_path, sr=None, mono=True)
            
            rms = librosa.feature.rms(y=y)[0]
            avg_rms = np.mean(rms)
            max_rms = np.max(rms)
            
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            avg_brightness = np.mean(spectral_centroid)
            
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            avg_zcr = np.mean(zcr)
            
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            avg_rolloff = np.mean(spectral_rolloff)
            
            dynamic_range = 20 * np.log10(max_rms / (avg_rms + 1e-10))
            
            return {
                "avg_rms": float(avg_rms),
                "max_rms": float(max_rms),
                "dynamic_range": float(dynamic_range),
                "brightness": float(avg_brightness),
                "zero_crossing_rate": float(avg_zcr),
                "spectral_rolloff": float(avg_rolloff),
                "duration": len(y) / sr
            }
        except Exception as e:
            logger.error(f"Track analysis failed: {e}")
            return {}
    
    def suggest_mix_parameters(self, beat_path: str, vocal_path: str, 
                               reference_analysis: Optional[Dict] = None) -> Dict:
        """
        Analyze beat and vocal tracks to suggest optimal mixing parameters.
        Uses reference track analysis if available.
        """
        try:
            beat_analysis = self.analyze_track(beat_path)
            vocal_analysis = self.analyze_track(vocal_path)
            
            if not beat_analysis or not vocal_analysis:
                defaults = self._default_mix_parameters()
                return {
                    "suggestions": defaults,
                    "reasoning": "Audio analysis unavailable. Using balanced default mix parameters for a clean, professional sound.",
                    "beat_analysis": {},
                    "vocal_analysis": {}
                }
            
            beat_volume = 0.8
            vocal_volume = 1.0
            
            if beat_analysis["avg_rms"] > vocal_analysis["avg_rms"] * 1.5:
                beat_volume = 0.6
                vocal_volume = 1.2
            elif beat_analysis["avg_rms"] < vocal_analysis["avg_rms"] * 0.5:
                beat_volume = 1.0
                vocal_volume = 0.8
            
            eq_low = 0
            eq_mid = 0
            eq_high = 0
            
            if beat_analysis["brightness"] > 3000:
                eq_high = -3
            
            if vocal_analysis["brightness"] < 2000:
                eq_high = +2
                eq_mid = +1
            
            compression = 0.5
            if vocal_analysis["dynamic_range"] > 15:
                compression = 0.7
            elif vocal_analysis["dynamic_range"] < 8:
                compression = 0.3
            
            reverb = 0.3
            if vocal_analysis["avg_rms"] < 0.1:
                reverb = 0.5
            
            limiter = 0.8
            
            if reference_analysis:
                ref_energy = reference_analysis.get("energy", 0.5)
                if ref_energy > 0.7:
                    compression = min(0.9, compression + 0.2)
                    limiter = 0.9
            
            suggestions = {
                "beat_volume": round(beat_volume, 2),
                "vocal_volume": round(vocal_volume, 2),
                "eq": {
                    "low": int(eq_low),
                    "mid": int(eq_mid),
                    "high": int(eq_high)
                },
                "compression": round(compression, 2),
                "reverb": round(reverb, 2),
                "limiter": round(limiter, 2)
            }
            
            reasoning = self._generate_reasoning(
                beat_analysis, vocal_analysis, suggestions, reference_analysis
            )
            
            self.suggested_params = suggestions
            
            return {
                "suggestions": suggestions,
                "reasoning": reasoning,
                "beat_analysis": beat_analysis,
                "vocal_analysis": vocal_analysis
            }
            
        except Exception as e:
            logger.error(f"Mix parameter suggestion failed: {e}")
            defaults = self._default_mix_parameters()
            return {
                "suggestions": defaults,
                "reasoning": "Using balanced default mix parameters. Manual adjustments recommended based on your track's character.",
                "beat_analysis": {},
                "vocal_analysis": {}
            }
    
    def _default_mix_parameters(self) -> Dict:
        """Return safe default mixing parameters"""
        return {
            "beat_volume": 0.8,
            "vocal_volume": 1.0,
            "eq": {"low": 0, "mid": 0, "high": 0},
            "compression": 0.5,
            "reverb": 0.3,
            "limiter": 0.8
        }
    
    def _generate_reasoning(self, beat_analysis: Dict, vocal_analysis: Dict,
                           suggestions: Dict, reference_analysis: Optional[Dict]) -> str:
        """Generate human-readable reasoning for mix suggestions"""
        reasons = []
        
        if suggestions["beat_volume"] < 0.7:
            reasons.append("Beat is loud compared to vocals, reducing beat volume for clarity")
        elif suggestions["beat_volume"] > 0.9:
            reasons.append("Beat is quiet, boosting volume to match vocal energy")
        
        if suggestions["eq"]["high"] > 0:
            reasons.append("Vocals need brightness, added high-end boost")
        elif suggestions["eq"]["high"] < 0:
            reasons.append("Beat is too bright, rolling off highs for warmth")
        
        if suggestions["compression"] > 0.6:
            reasons.append("Vocals have wide dynamic range, applying compression for consistency")
        
        if suggestions["reverb"] > 0.4:
            reasons.append("Vocals are dry, adding reverb for depth and space")
        
        if reference_analysis:
            reasons.append("Adjusted parameters to match reference track energy and vibe")
        
        if not reasons:
            reasons.append("Balanced mix based on standard industry practices")
        
        return ". ".join(reasons) + "."
    
    def auto_mix_voice_response(self, reasoning: str) -> str:
        """Generate voice response from Tone (Mix Engineer) explaining the auto-mix"""
        return f"I analyzed your tracks and here's what I'm thinking: {reasoning} Let's see how it sounds!"
