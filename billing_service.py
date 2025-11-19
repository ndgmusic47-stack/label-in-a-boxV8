"""
Billing Service - Business logic for Stripe webhook handling
"""

import os
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from crud.user import UserRepository
from models import User

logger = logging.getLogger(__name__)

# Initialize Stripe (for fetching customer metadata)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


class BillingService:
    """
    Service class for handling billing-related business logic.
    Uses dependency injection for database session and user repository.
    """
    
    def __init__(self, db: AsyncSession, user_repo: UserRepository):
        """
        Initialize the billing service.
        
        Args:
            db: AsyncSession instance for database operations
            user_repo: UserRepository instance for user operations
        """
        self.db = db
        self.user_repo = user_repo
    
    async def handle_subscription_update(self, event: stripe.Event) -> bool:
        """
        Handle Stripe subscription update webhook.
        
        This method processes verified Stripe webhook events to update user subscription status.
        It extracts the user_id from Stripe Customer metadata and updates the user's
        is_paid_user status based on the subscription status.
        
        Args:
            event: Verified Stripe Event object (from webhook signature verification)
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Extract event type and data from verified Stripe Event object
            event_type = event.type
            event_data = event.data
            event_object = event_data.object
            
            # Handle subscription-related events
            if event_type in [
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.deleted",
                "checkout.session.completed"
            ]:
                # Extract customer information
                customer_id = None
                customer_metadata = {}
                
                if event_type == "checkout.session.completed":
                    # For checkout.session.completed, customer is in the object
                    customer_id = getattr(event_object, "customer", None)
                else:
                    # For subscription events, customer is in the object
                    customer_id = getattr(event_object, "customer", None)
                    # Try to get metadata from subscription object first (if available)
                    # Stripe objects support attribute access
                    customer_metadata = getattr(event_object, "metadata", None)
                
                # Extract user_id from metadata
                # Stripe Customer metadata should contain user_id
                # Metadata is typically a dict in Stripe objects
                user_id_str = None
                if customer_metadata:
                    if isinstance(customer_metadata, dict):
                        user_id_str = customer_metadata.get("user_id")
                    else:
                        user_id_str = getattr(customer_metadata, "user_id", None)
                
                # If not in subscription/checkout metadata, fetch customer from Stripe
                if not user_id_str and customer_id:
                    try:
                        # Fetch customer object from Stripe to get metadata
                        customer = stripe.Customer.retrieve(customer_id)
                        customer_metadata = getattr(customer, "metadata", None)
                        if customer_metadata:
                            if isinstance(customer_metadata, dict):
                                user_id_str = customer_metadata.get("user_id")
                            else:
                                user_id_str = getattr(customer_metadata, "user_id", None)
                    except Exception as e:
                        logger.error(f"Failed to fetch customer {customer_id} from Stripe: {e}")
                
                if not user_id_str:
                    logger.error(f"Could not extract user_id from Stripe payload for customer {customer_id}")
                    return False
                
                # Convert user_id to integer
                try:
                    user_id = int(user_id_str)
                except (ValueError, TypeError):
                    logger.error(f"Invalid user_id format: {user_id_str}")
                    return False
                
                # Retrieve user from database
                user = await self.user_repo.get_user_by_id(user_id)
                if not user:
                    logger.error(f"User not found for user_id: {user_id}")
                    return False
                
                # Extract subscription status
                subscription_status = None
                if event_type == "checkout.session.completed":
                    # Checkout completed means subscription is active
                    subscription_status = "active"
                elif event_type == "customer.subscription.deleted":
                    subscription_status = "canceled"
                else:
                    # For subscription.created or subscription.updated
                    # Stripe objects support attribute access
                    subscription_status = getattr(event_object, "status", "")
                    if subscription_status:
                        subscription_status = subscription_status.lower()
                    else:
                        subscription_status = ""
                
                # Update user based on subscription status
                if subscription_status == "active":
                    # Set is_paid_user to True
                    await self.user_repo.update_user(user, {"is_paid_user": True})
                    await self.db.commit()
                    logger.info(f"Updated user {user_id} to paid status (active subscription)")
                elif subscription_status in ["canceled", "unpaid", "past_due", "incomplete_expired"]:
                    # Set is_paid_user to False
                    await self.user_repo.update_user(user, {"is_paid_user": False})
                    await self.db.commit()
                    logger.info(f"Updated user {user_id} to free status (subscription: {subscription_status})")
                else:
                    logger.warning(f"Unhandled subscription status: {subscription_status} for user {user_id}")
                
                return True
            
            # For other event types, log and return True (not an error, just not handled)
            logger.info(f"Unhandled event type: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing subscription update: {e}", exc_info=True)
            await self.db.rollback()
            return False

