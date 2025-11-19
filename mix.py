"""
Mix-related request models
"""
from pydantic import BaseModel
from typing import Optional


class CleanMixRequest(BaseModel):
    session_id: str
    vocal_url: str
    beat_url: str
    user_id: Optional[str] = None
    plan: Optional[str] = "free"
    trial_started_at: Optional[str] = None
    subscription_active: Optional[bool] = False

