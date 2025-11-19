"""
Analytics Router - API endpoints for analytics
"""
from fastapi import APIRouter, Depends
from pathlib import Path

from auth import get_current_user
from services.analytics_service import AnalyticsService
from backend.utils.responses import success_response, error_response
from utils.shared_utils import get_session_media_path, log_endpoint_event

# Create router
analytics_router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Service instance
analytics_service = AnalyticsService()

# Constants
MEDIA_DIR = Path("./media")


@analytics_router.get("/session/{session_id}")
async def get_session_analytics(session_id: str, current_user: dict = Depends(get_current_user)):
    """Phase 2.2: Get analytics for a specific session (safe demo metrics)"""
    try:
        session_path = get_session_media_path(session_id, current_user["user_id"])
        analytics = await analytics_service.get_session_analytics(
            session_id=session_id,
            user_id=current_user["user_id"],
            session_path=session_path
        )
        
        log_endpoint_event("/analytics/session/{id}", session_id, "success", {})
        return success_response(
            data={"analytics": analytics},
            message="Session analytics retrieved successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/analytics/session/{id}", session_id, "error", {"error": str(e)})
        return error_response(f"Analytics failed: {str(e)}")


@analytics_router.get("/dashboard/all")
async def get_dashboard_analytics():
    """Phase 2.2: Get dashboard analytics across all sessions (safe demo metrics)"""
    try:
        dashboard_data = await analytics_service.get_dashboard_analytics()
        
        log_endpoint_event("/analytics/dashboard/all", None, "success", {
            "projects": dashboard_data["dashboard"]["total_projects"]
        })
        return success_response(
            data=dashboard_data,
            message="Dashboard analytics retrieved successfully"
        )
    
    except Exception as e:
        log_endpoint_event("/analytics/dashboard/all", None, "error", {"error": str(e)})
        return error_response(f"Dashboard analytics failed: {str(e)}")

