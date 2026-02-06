"""
PostMonitorService for detecting new posts in channels and routing to appropriate services
"""

import logging
from typing import Optional, Dict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot, Message
from telegram.error import TelegramError

from ..models.channel import Channel
from .reaction_boost_service import ReactionBoostService

logger = logging.getLogger(__name__)


class PostMonitorService:
    """Service for monitoring channels and detecting new posts"""
    
    def __init__(self, bot: Bot, db_session: AsyncSession, 
                 reaction_service: Optional[ReactionBoostService] = None):
        """
        Initialize PostMonitorService
        
        Args:
            bot: Telegram Bot instance
            db_session: SQLAlchemy async session for database operations
            reaction_service: ReactionBoostService instance for boosting posts (optional)
        
        Requirements: 3.1
        """
        self.bot = bot
        self.db = db_session
        self.reaction_service = reaction_service
        self.last_checked: Dict[int, int] = {}  # channel_id -> last_message_id
        logger.info("PostMonitorService initialized")
    
    async def monitor_channels(self) -> None:
        """
        Main monitoring loop - polls channels for new posts
        
        This method:
        1. Fetches all active channels from the database
        2. For each channel, fetches new posts since last check
        3. Routes posts to appropriate services based on channel mode
        4. Handles exceptions and logs errors
        
        Requirements: 1.4, 1.5, 3.1
        """
        try:
            # Requirement 5.5: Get active channels
            channels = await self._get_active_channels()
            logger.info(f"Monitoring {len(channels)} active channels")
            
            for channel in channels:
                try:
                    # Requirement 3.1: Fetch new posts for this channel
                    new_posts = await self._fetch_new_posts(channel)
                    
                    if new_posts:
                        logger.info(f"Found {len(new_posts)} new posts in channel {channel.channel_id}")
                    
                    for post in new_posts:
                        # Requirement 1.5: Route to reaction service if reaction mode enabled
                        if (channel.mode == 'reaction' or channel.mode == 'both') and self.reaction_service:
                            try:
                                await self.reaction_service.boost_post(channel, post)
                            except Exception as e:
                                logger.error(
                                    f"Error boosting post {post.message_id} in channel {channel.channel_id}: {e}",
                                    exc_info=True
                                )
                        
                        # Requirement 1.4: Route to comment service if comment mode enabled
                        # Note: Comment monitoring is handled separately by CommentMonitor service
                        # This is just a placeholder for future integration
                        if channel.mode == 'comment' or channel.mode == 'both':
                            # Comment monitoring happens in discussion groups, not channels
                            pass
                
                except TelegramError as e:
                    logger.error(
                        f"Telegram API error for channel {channel.channel_id}: {e}",
                        exc_info=True
                    )
                    await self._log_error(channel, e)
                except Exception as e:
                    logger.error(
                        f"Unexpected error monitoring channel {channel.channel_id}: {e}",
                        exc_info=True
                    )
                    await self._log_error(channel, e)
        
        except Exception as e:
            logger.error(f"Error in monitor_channels main loop: {e}", exc_info=True)
    
    async def _get_active_channels(self) -> list[Channel]:
        """
        Query database for active channels
        
        Returns:
            List of active Channel model instances
        
        Requirements: 5.5
        """
        try:
            # Query for active channels
            result = await self.db.execute(
                select(Channel).where(
                    Channel.is_active == True
                )
            )
            channels = result.scalars().all()
            return list(channels)
        except Exception as e:
            logger.error(f"Error fetching active channels: {e}", exc_info=True)
            return []
    
    async def _fetch_new_posts(self, channel: Channel) -> list[Message]:
        """
        Fetch posts newer than last checked message ID
        
        Args:
            channel: Channel model instance to fetch posts from
        
        Returns:
            List of new Message objects
        
        Requirements: 3.1
        """
        try:
            channel_id = str(channel.channel_id)
            
            # Get the last message ID we checked for this channel
            last_message_id = self.last_checked.get(channel.id, 0)
            
            # Fetch recent messages from the channel
            # We'll get the latest message to check if there are new posts
            try:
                # Get chat to verify we have access
                chat = await self.bot.get_chat(channel_id)
                
                # Try to get recent messages
                # Note: Telegram Bot API doesn't have a direct "get messages" method
                # We need to use get_updates or rely on webhooks for real-time detection
                # For now, we'll implement a basic approach using message IDs
                
                # Get the latest message by trying to forward it (without actually forwarding)
                # This is a workaround since bots can't directly fetch channel messages
                # In production, this should use webhooks or channel_post updates
                
                # For now, return empty list as we need webhook integration
                # This will be populated when the bot receives channel_post updates
                new_posts = []
                
                # Update last_checked even if no new posts
                # This will be updated when we actually receive posts via updates
                
                return new_posts
                
            except TelegramError as e:
                logger.warning(f"Could not fetch messages from channel {channel_id}: {e}")
                return []
        
        except Exception as e:
            logger.error(f"Error in _fetch_new_posts for channel {channel.id}: {e}", exc_info=True)
            return []
    
    async def process_channel_post(self, channel: Channel, post: Message) -> None:
        """
        Process a single channel post received via update
        
        This method should be called when the bot receives a channel_post update.
        It checks if the post is new and routes it to appropriate services.
        
        Args:
            channel: Channel model instance
            post: Message object from Telegram update
        
        Requirements: 3.1, 1.4, 1.5
        """
        try:
            # Check if this is a new post (not already processed)
            last_message_id = self.last_checked.get(channel.id, 0)
            
            if post.message_id <= last_message_id:
                # Already processed this post
                return
            
            # Update last checked message ID
            self.last_checked[channel.id] = post.message_id
            
            logger.info(f"Processing new post {post.message_id} in channel {channel.channel_id}")
            
            # Requirement 1.5: Route to reaction service if reaction mode enabled
            if (channel.mode == 'reaction' or channel.mode == 'both') and self.reaction_service:
                try:
                    await self.reaction_service.boost_post(channel, post)
                except Exception as e:
                    logger.error(
                        f"Error boosting post {post.message_id} in channel {channel.channel_id}: {e}",
                        exc_info=True
                    )
            
            # Requirement 1.4: Comment mode handling
            # Comment monitoring happens in discussion groups, handled separately
            
        except Exception as e:
            logger.error(f"Error processing channel post: {e}", exc_info=True)
    
    async def _log_error(self, channel: Channel, error: Exception) -> None:
        """
        Log errors during monitoring
        
        Args:
            channel: Channel where error occurred
            error: Exception that was raised
        """
        try:
            # Import here to avoid circular dependency
            from .activity_logger import ActivityLogger
            
            logger_service = ActivityLogger(self.db)
            await logger_service.log_error(
                channel.id,
                None,  # No specific post_id for monitoring errors
                'monitoring_error',
                {
                    'error': str(error),
                    'error_type': type(error).__name__,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}", exc_info=True)
