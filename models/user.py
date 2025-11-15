from datetime import datetime
from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    email: str
    password_hash: str
    created_at: datetime
    plan: str = "free"  # free or pro

