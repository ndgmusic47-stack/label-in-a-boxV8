"""
Authentication routes and dependencies
"""

import uuid
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import re
import stripe

from database import load_users, save_users
from auth_utils import hash_password, verify_password, create_jwt, decode_jwt

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET", "sk_test_placeholder")

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


@auth_router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Create a new user account"""
    try:
        # Validate email format
        if not validate_email(request.email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Validate password length
        if len(request.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Load existing users
        users = load_users()
        
        # Check if email already exists
        for user_id, user_data in users.items():
            if user_data.get("email") == request.email.lower():
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(request.password)
        
        users[user_id] = {
            "email": request.email.lower(),
            "password_hash": password_hash,
            "created_at": datetime.utcnow(),
            "plan": "free"  # Default to free plan
        }
        
        # Create Stripe customer
        try:
            customer = stripe.Customer.create(
                email=request.email.lower(),
                metadata={"user_id": user_id}
            )
            users[user_id]["stripe_customer_id"] = customer.id
        except Exception as e:
            # Log error but don't fail signup if Stripe is unavailable
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create Stripe customer: {e}")
        
        # Save users
        save_users(users)
        
        # Generate JWT token
        token = create_jwt(user_id)
        
        return AuthResponse(
            ok=True,
            token=token,
            user_id=user_id,
            message="User created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@auth_router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login and get JWT token"""
    try:
        # Load users
        users = load_users()
        
        # Find user by email
        user_id = None
        user_data = None
        for uid, data in users.items():
            if data.get("email") == request.email.lower():
                user_id = uid
                user_data = data
                break
        
        if not user_id or not user_data:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not verify_password(request.password, user_data["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Generate JWT token
        token = create_jwt(user_id)
        
        return AuthResponse(
            ok=True,
            token=token,
            user_id=user_id,
            message="Login successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@auth_router.get("/me")
async def get_current_user_info(
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """Get current user information from JWT token"""
    try:
        # Extract token from Authorization header
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")
        
        # Check if Bearer token
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid Authorization header format")
        
        token = authorization.replace("Bearer ", "").strip()
        
        # Decode token
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Load users and verify user exists
        users = load_users()
        if user_id not in users:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_data = users[user_id]
        
        # Return user info (without password hash)
        return {
            "ok": True,
            "user_id": user_id,
            "email": user_data["email"],
            "plan": user_data.get("plan", "free"),  # Default to free if not set
            "created_at": user_data["created_at"].isoformat() if isinstance(user_data["created_at"], datetime) else user_data["created_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@auth_router.post("/logout")
async def logout():
    """Logout (client-side token deletion)"""
    return {
        "ok": True,
        "message": "Logged out successfully. Please delete the token on the client side."
    }


# Dependency for protected routes
async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> dict:
    """Dependency function to get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Check if Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # Decode token
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Load users and verify user exists
    users = load_users()
    if user_id not in users:
        raise HTTPException(status_code=401, detail="User not found")
    
    user_data = users[user_id].copy()
    user_data["user_id"] = user_id
    # Ensure plan field exists, default to "free"
    if "plan" not in user_data:
        user_data["plan"] = "free"
    return user_data

