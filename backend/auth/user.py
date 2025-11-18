from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    plan: str = "free"
    trial_started_at: str | None = None
    subscription_active: bool = False

