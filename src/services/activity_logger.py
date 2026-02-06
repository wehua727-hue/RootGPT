"""
ActivityLogger service for logging reaction boost activities
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.activity_log import ActivityLog


class ActivityLogger:
    """Service for logging reaction boost activities and errors"""
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize ActivityLogger with database session
        
        Args:
            db_session: SQLAlchemy async session for database operations
        """
        self.db = db_session
    
    async def log_reaction_added(self, channel_id: int, post_id: int, emoji: str) -> None:
        """
        Log individual reaction addition
        
        Args:
            channel_id: Database ID of the channel
            post_id: Telegram message ID of the post
            emoji: The emoji that was added as a reaction
        
        Requirements: 6.1
        """
        log = ActivityLog(
            channel_id=channel_id,
            post_id=post_id,
            activity_type='reaction_added',
            details={'emoji': emoji},
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(log)
        await self.db.commit()
    
    async def log_boost_completed(self, channel_id: int, post_id: int, 
                                  reaction_count: int) -> None:
        """
        Log completion of post boosting
        
        Args:
            channel_id: Database ID of the channel
            post_id: Telegram message ID of the post
            reaction_count: Total number of reactions added to the post
        
        Requirements: 6.2
        """
        log = ActivityLog(
            channel_id=channel_id,
            post_id=post_id,
            activity_type='boost_completed',
            details={'reaction_count': reaction_count},
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(log)
        await self.db.commit()
    
    async def log_error(self, channel_id: int, post_id: Optional[int],
                       error_type: str, details: dict) -> None:
        """
        Log errors during boosting
        
        Args:
            channel_id: Database ID of the channel
            post_id: Telegram message ID of the post (optional, may be None for channel-level errors)
            error_type: Type of error (e.g., 'permission_error', 'rate_limit', 'unknown_error')
            details: Dictionary containing error-specific details
        
        Requirements: 6.3
        """
        log = ActivityLog(
            channel_id=channel_id,
            post_id=post_id,
            activity_type='error',
            details={'error_type': error_type, **details},
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(log)
        await self.db.commit()
