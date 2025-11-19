"""
Social Router - API endpoints for social media post scheduling
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from auth import get_current_user
from services.social_service import SocialService
from backend.utils.responses import success_response, error_response
from utils.shared_utils import get_session_media_path, log_endpoint_event

# Create router
social_router = APIRouter(prefix="/api/social", tags=["social"])

# Service instance
social_service = SocialService()


# Request models
class SocialPostRequest(BaseModel):
    session_id: str
    platform: str = Field(default="tiktok", description="tiktok, shorts, or reels")
    when_iso: str = Field(default="", description="ISO datetime string")
    caption: str = Field(default="", description="Post caption")


@social_router.get("/platforms")
async def get_social_platforms():
    """Return supported platforms"""
    try:
        platforms_data = await social_service.get_platforms()
        log_endpoint_event("/social/platforms", None, "success", {})
        return success_response(
            data=platforms_data,
            message="Platforms retrieved successfully"
        )
    except Exception as e:
        log_endpoint_event("/social/platforms", None, "error", {"error": str(e)})
        return error_response(f"Failed to get platforms: {str(e)}")


@social_router.post("/posts")
async def create_social_post(request: SocialPostRequest, current_user: dict = Depends(get_current_user)):
    """Schedule a social post using GetLate.dev API or local JSON fallback"""
    try:
        session_path = get_session_media_path(request.session_id, current_user["user_id"])
        
        result = await social_service.create_social_post(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            session_path=session_path,
            platform=request.platform,
            when_iso=request.when_iso,
            caption=request.caption
        )
        
        provider = result.get("provider", "local")
        platform = request.platform or "tiktok"
        
        log_endpoint_event("/social/posts", request.session_id, "success", {
            "platform": platform,
            "provider": provider
        })
        
        if provider == "getlate":
            return success_response(
                data=result,
                message=f"Post scheduled on {platform} via GetLate.dev"
            )
        else:
            return success_response(
                data=result,
                message=f"Post scheduled locally on {platform} (GetLate API key not configured)"
            )
    
    except ValueError as e:
        log_endpoint_event("/social/posts", request.session_id, "error", {"error": str(e)})
        return error_response(str(e))
    except Exception as e:
        log_endpoint_event("/social/posts", request.session_id, "error", {"error": str(e)})
        return error_response(f"Social post scheduling failed: {str(e)}")

