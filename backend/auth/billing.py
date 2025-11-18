from datetime import datetime, timedelta
from backend.auth.user import User


TRIAL_DAYS = 3


def is_trial_active(user: User) -> bool:
    if not user.trial_started_at:
        return False
    start = datetime.fromisoformat(user.trial_started_at)
    return datetime.utcnow() < start + timedelta(days=TRIAL_DAYS)


def user_can_use_feature(user: User, feature: str) -> bool:
    if user.subscription_active:
        return True
    if is_trial_active(user):
        return True
    if feature in ["beat", "lyrics"]:
        return True
    return False

