"""
Mix request models
"""

from pydantic import BaseModel, Field
from typing import Optional


class MixRequest(BaseModel):
    session_id: str
    vocal_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    beat_gain: float = Field(default=0.8, ge=0.0, le=2.0)
    hpf_hz: int = Field(default=80, ge=20, le=200, description="High-pass filter frequency")
    deess_amount: float = Field(default=0.3, ge=0.0, le=1.0, description="De-ess amount")


class MixApplyRequest(BaseModel):
    session_id: str
    job_id: Optional[str] = None

