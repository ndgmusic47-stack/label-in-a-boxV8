"""
Shared utility functions for routers and services
"""
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def get_session_media_path(session_id: str, user_id: str) -> Path:
    """
    Phase 8B:
    User-scoped media path. No backward compatibility.
    """
    path = Path("./media") / user_id / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def log_endpoint_event(endpoint: str, session_id: Optional[str] = None, result: str = "success", details: Optional[dict] = None):
    """Log endpoint execution to app.log"""
    log_data = {
        "endpoint": endpoint,
        "session_id": session_id or "none",
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        log_data.update(details)
    logger.info(f"{endpoint} | session={session_id} | {result} | {json.dumps(details or {})}")

