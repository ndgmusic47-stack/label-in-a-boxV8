import json
import os
from pathlib import Path
from datetime import datetime

USER_DB_PATH = Path("data/users.json")


def load_users():
    """Load users from JSON file"""
    if not USER_DB_PATH.exists():
        return {}
    with open(USER_DB_PATH, "r") as f:
        data = json.load(f)
        # Convert datetime strings back to datetime objects for created_at
        for user_id, user_data in data.items():
            if isinstance(user_data.get("created_at"), str):
                data[user_id]["created_at"] = datetime.fromisoformat(user_data["created_at"])
        return data


def save_users(users):
    """Save users to JSON file"""
    USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Convert datetime objects to ISO strings for JSON serialization
    serializable_users = {}
    for user_id, user_data in users.items():
        serializable_users[user_id] = user_data.copy()
        if isinstance(user_data.get("created_at"), datetime):
            serializable_users[user_id]["created_at"] = user_data["created_at"].isoformat()
    with open(USER_DB_PATH, "w") as f:
        json.dump(serializable_users, f, indent=4)

