"""
Billing Router - API endpoints for Stripe billing webhooks
"""

import os
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, Body, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
import stripe.error

from database import get_db
from crud.user import UserRepository
from services.billing_service import BillingService

logger = logging.getLogger(__name__)

# Create billing router
billing_router = APIRouter(prefix="/api/billing", tags=["billing"])


@billing_router.post("/webhook")
async def stripe_webhook(
    payload: bytes = Body(...),
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events with signature verification.
    
    This endpoint verifies the Stripe webhook signature before processing events.
    Only verified events are processed to prevent spoofing attacks.
    
    Args:
        payload: Raw request body as bytes (required for Stripe signature verification)
        stripe_signature: Stripe signature header value
        db: Database session dependency
        
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Load webhook secret from environment variables
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET environment variable is not set")
            raise HTTPException(
                status_code=500,
                detail="Webhook secret not configured"
            )
        
        # Verify webhook signature using Stripe's construct_event method
        try:
            event = stripe.webhook.construct_event(
                payload,
                stripe_signature,
                webhook_secret
            )
        except stripe.error.SignatureVerificationError as e:
            # Signature verification failed - this is a fake request
            logger.error(f"Stripe webhook signature verification failed: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid webhook signature"
            )
        except ValueError as e:
            # Invalid payload format
            logger.error(f"Invalid webhook payload: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid payload format"
            )
        
        # Initialize service with dependency injection
        user_repo = UserRepository(db)
        billing_service = BillingService(db, user_repo)
        
        # Process the verified webhook event
        success = await billing_service.handle_subscription_update(event)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={"ok": True, "received": True}
            )
        else:
            # Log error but still return 200 to Stripe (to prevent retries)
            logger.error("Webhook processing failed but returning 200 to prevent Stripe retries")
            return JSONResponse(
                status_code=200,
                content={"ok": False, "received": True, "error": "Processing failed"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        # Return 200 to Stripe even on error to prevent retries
        # In production, you might want to return 500 for certain errors
        return JSONResponse(
            status_code=200,
            content={"ok": False, "received": True, "error": str(e)}
        )

