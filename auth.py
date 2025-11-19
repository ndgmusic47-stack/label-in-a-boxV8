"""
Authentication routes and dependencies
"""

import os
from types import SimpleNamespace
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import re
import stripe

from database import get_db
from crud.user import UserRepository
from auth_utils import hash_password, verify_password, create_jwt, decode_jwt
from services.trial_service import TrialService
from utils.shared_utils import get_cached

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")

# Create auth router
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request models
class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


# Response models
class AuthResponse(BaseModel):
    ok: bool
    token: Optional[str] = None
    user_id: Optional[str] = None
    message: Optional[str] = None


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@auth_router.post("/signup")
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account"""
    try:
        # Validate email format
        if not validate_email(request.email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Validate password length
        if len(request.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Initialize repository
        user_repo = UserRepository(db)
        
        # Check if email already exists
        existing_user = await user_repo.get_user_by_email(request.email.lower())
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create new user
        user_data = {
            "email": request.email.lower(),
            "hashed_password": password_hash,
            "is_active": True,
            "is_paid_user": False  # Default to free plan
        }
        
        user = await user_repo.create_user(user_data)
        
        # Start trial period for new user
        trial_service = TrialService(db, user_repo)
        await trial_service.start_trial(user)
        
        # Create Stripe customer
        try:
            customer = stripe.Customer.create(
                email=request.email.lower(),
                metadata={"user_id": str(user.id)}
            )
            # Note: stripe_customer_id would need to be added to User model if needed
        except Exception as e:
            # Log error but don't fail signup if Stripe is unavailable
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create Stripe customer: {e}")
        
        # Generate JWT token with user ID
        token = create_jwt(str(user.id))
        
        # Create response with httpOnly cookie
        # JWT expiration is 7 days = 604800 seconds
        response = JSONResponse(
            content={
                "ok": True,
                "user_id": str(user.id)
            }
        )
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=604800  # 7 days in seconds
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@auth_router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get JWT token"""
    try:
        # Initialize repository
        user_repo = UserRepository(db)
        
        # Find user by email
        user = await user_repo.get_user_by_email(request.email.lower())
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User account is inactive")
        
        # Generate JWT token
        token = create_jwt(str(user.id))
        
        # Create response with httpOnly cookie
        # JWT expiration is 7 days = 604800 seconds
        response = JSONResponse(
            content={
                "ok": True,
                "user_id": str(user.id)
            }
        )
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=604800  # 7 days in seconds
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@auth_router.get("/me")
async def get_current_user_info(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    auth_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information from JWT token"""
    try:
        # Extract token from cookie (preferred) or Authorization header (fallback)
        token = None
        if auth_token:
            token = auth_token
        elif authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "").strip()
        
        if not token:
            raise HTTPException(status_code=401, detail="Missing authentication token")
        
        # Decode token
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Convert user_id to integer (JWT stores it as string)
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid user ID in token")
        
        # Initialize repository and get user (with caching)
        user_repo = UserRepository(db)
        
        # Cache user lookup for 300 seconds (5 minutes)
        async def fetch_user():
            user = await user_repo.get_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            # Convert User object to dict for caching
            return {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "is_paid_user": user.is_paid_user,
                "trial_start_date": user.trial_start_date
            }
        
        user_dict = await get_cached(
            key=f"user:{user_id}",
            fallback_func=fetch_user,
            ttl_seconds=300
        )
        
        # Create a simple object from dict for attribute access
        user = SimpleNamespace(**user_dict)
        
        # Determine plan based on is_paid_user
        plan = "pro" if user.is_paid_user else "free"
        
        # Return user info (without password hash)
        return {
            "ok": True,
            "user_id": str(user.id),
            "email": user.email,
            "plan": plan,
            "is_paid_user": user.is_paid_user,
            "is_active": user.is_active
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@auth_router.post("/logout")
async def logout():
    """Logout and clear auth token cookie"""
    response = JSONResponse(
        content={
            "ok": True,
            "message": "Logged out successfully"
        }
    )
    # Clear the auth_token cookie by setting max_age=0
    response.set_cookie(
        key="auth_token",
        value="",
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=0
    )
    return response


# Dependency for protected routes
async def get_current_user(
    auth_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency function to get current authenticated user.
    
    Authentication priority:
    1. Check auth_token cookie first (httpOnly cookie set by login/signup)
    2. Fallback to Authorization header (Bearer token) for API consumers
    3. Raise 401 if neither is found
    """
    # Extract token: check cookie first, then Authorization header
    token = None
    
    # Priority 1: Check httpOnly cookie (preferred for browser clients)
    if auth_token:
        token = auth_token
    # Priority 2: Fallback to Authorization header (for API consumers)
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "").strip()
    
    # No token found in either location
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    # Decode token
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Convert user_id to integer (JWT stores it as string)
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token")
    
    # Initialize repository and get user (with caching)
    user_repo = UserRepository(db)
    
    # Cache user lookup for 300 seconds (5 minutes)
    async def fetch_user():
        user = await user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Convert User object to dict for caching
        return {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "is_paid_user": user.is_paid_user,
            "trial_start_date": user.trial_start_date
        }
    
    user_dict = await get_cached(
        key=f"user:{user_id}",
        fallback_func=fetch_user,
        ttl_seconds=300
    )
    
    # Create a simple object from dict for attribute access
    user = SimpleNamespace(**user_dict)
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")
    
    # Convert User model to dict format expected by other parts of the application
    user_data = {
        "user_id": str(user.id),
        "email": user.email,
        "plan": "pro" if user.is_paid_user else "free",
        "is_paid_user": user.is_paid_user,
        "is_active": user.is_active,
        "trial_start_date": user.trial_start_date
    }
    
    return user_data

