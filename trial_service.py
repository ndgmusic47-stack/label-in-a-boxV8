"""
Trial Service for managing 3-day (72 hour) trial periods
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from crud.user import UserRepository
from models import User


class TrialService:
    """
    Service for managing user trial periods.
    Handles trial start and validation logic.
    """
    
    def __init__(self, db: AsyncSession, user_repo: UserRepository):
        """
        Initialize the trial service with database session and user repository.
        
        Args:
            db: AsyncSession instance for database operations
            user_repo: UserRepository instance for user operations
        """
        self.db = db
        self.user_repo = user_repo
    
    async def start_trial(self, user: User) -> None:
        """
        Start a trial period for a user by setting trial_start_date.
        Only sets the date if it's currently None (hasn't started yet).
        
        Args:
            user: User object to start trial for
        """
        # Only set trial_start_date if it's currently None
        if user.trial_start_date is None:
            trial_start = datetime.utcnow().isoformat()
            await self.user_repo.update_user(user, {"trial_start_date": trial_start})
    
    def is_trial_active(self, user: User) -> bool:
        """
        Check if a user's trial is currently active.
        
        A trial is active if:
        1. User is NOT a paid user (is_paid_user is False)
        2. trial_start_date is set (not None)
        3. Less than 72 hours (3 days) have elapsed since trial_start_date
        
        Args:
            user: User object to check
            
        Returns:
            True if trial is active, False otherwise
        """
        # Paid users don't have active trials (they have paid access)
        if user.is_paid_user:
            return False
        
        # Trial must have started
        if user.trial_start_date is None:
            return False
        
        try:
            # Parse the ISO format string to datetime
            trial_start = datetime.fromisoformat(user.trial_start_date)
            
            # Calculate time elapsed since trial start
            now = datetime.utcnow()
            time_elapsed = now - trial_start
            
            # Trial is active if less than 72 hours (3 days) have passed
            return time_elapsed < timedelta(hours=72)
        except (ValueError, TypeError) as e:
            # If parsing fails, consider trial inactive
            return False

