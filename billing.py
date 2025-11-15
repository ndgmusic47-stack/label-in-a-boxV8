"""
Billing routes for Stripe integration
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import stripe

from database import load_users, save_users
from auth import get_current_user

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET", "sk_test_placeholder")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
PRICE_PRO_MONTHLY = os.getenv("PRICE_PRO_MONTHLY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

logger = logging.getLogger(__name__)

# Create billing router
billing_router = APIRouter(prefix="/api/billing", tags=["billing"])


# Request models
class CreateCheckoutSessionRequest(BaseModel):
    userId: str
    priceId: Optional[str] = None


@billing_router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe Checkout Session for subscription"""
    try:
        # Verify user is authenticated and matches request
        if current_user["user_id"] != request.userId:
            raise HTTPException(status_code=403, detail="User mismatch")
        
        # Load user to get Stripe customer ID
        users = load_users()
        user_id = request.userId
        if user_id not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = users[user_id]
        customer_id = user_data.get("stripe_customer_id")
        
        if not customer_id:
            raise HTTPException(status_code=400, detail="Stripe customer not found. Please contact support.")
        
        # Use provided priceId or default from env
        price_id = request.priceId or PRICE_PRO_MONTHLY
        if not price_id:
            raise HTTPException(status_code=500, detail="Price ID not configured")
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=FRONTEND_URL + "/billing/success",
            cancel_url=FRONTEND_URL + "/billing/cancel"
        )
        
        logger.info(f"Created checkout session for user {user_id}: {session.id}")
        
        return {
            "ok": True,
            "url": session.url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@billing_router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle subscription events
        if event["type"] == "customer.subscription.created" or event["type"] == "checkout.session.completed":
            # Extract customer ID
            customer_id = None
            if event["type"] == "customer.subscription.created":
                customer_id = event["data"]["object"]["customer"]
            elif event["type"] == "checkout.session.completed":
                customer_id = event["data"]["object"]["customer"]
            
            if customer_id:
                # Load users and find user by Stripe customer ID
                users = load_users()
                user_id = None
                for uid, user_data in users.items():
                    if user_data.get("stripe_customer_id") == customer_id:
                        user_id = uid
                        break
                
                if user_id:
                    # Update user plan to "pro"
                    users[user_id]["plan"] = "pro"
                    save_users(users)
                    logger.info(f"Upgraded user {user_id} to pro plan via webhook")
                else:
                    logger.warning(f"User not found for Stripe customer {customer_id}")
        
        return {"ok": True, "received": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")


@billing_router.post("/portal")
async def create_portal_session(
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe Billing Portal session"""
    try:
        user_id = current_user["user_id"]
        
        # Load user to get Stripe customer ID
        users = load_users()
        if user_id not in users:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = users[user_id]
        customer_id = user_data.get("stripe_customer_id")
        
        if not customer_id:
            raise HTTPException(status_code=400, detail="Stripe customer not found. Please contact support.")
        
        # Create billing portal session
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=FRONTEND_URL + "/dashboard"
        )
        
        logger.info(f"Created billing portal session for user {user_id}: {session.id}")
        
        return {
            "ok": True,
            "url": session.url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")

