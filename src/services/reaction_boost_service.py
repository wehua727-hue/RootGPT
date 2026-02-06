"""
ReactionBoostService for adding reactions to channel posts
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter, TelegramForbiddenError

from ..models.boosted_post import BoostedPost
from ..models.channel import Channel
from ..models.reaction_settings import ReactionSettings
from .activity_logger import ActivityLogger


class ReactionBoostService:
    """Service for boosting reactions on channel posts"""
    
    def __init__(self, bot: Bot, db_session: AsyncSession):
        """
        Initialize ReactionBoostService
        
        Args:
            bot: Telegram Bot instance
            db_session: SQLAlchemy async session for database operations
        
        Requirements: 3.1, 3.2
        """
        self.bot = bot
        self.db = db_session
        self.logger = ActivityLogger(db_session)
        self.max_retries = 3
    
    async def boost_post(self, channel: Channel, post: Message) -> None:
        """
        Main entry point for boosting a post with reactions
        
        Args:
            channel: Channel model instance with configuration
            post: Telegram Message object representing the post
        
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"boost_post called for channel {channel.id}, post {post.message_id}")
        
        # Requirement 3.6: Check if already boosted (early return)
        if await self._is_already_boosted(channel.id, post.message_id):
            logger.info(f"Post {post.message_id} already boosted, skipping")
            return
        
        # Requirement 3.2: Parse and validate reaction settings
        if not channel.reaction_settings:
            logger.warning(f"Channel {channel.id} has no reaction_settings")
            return
        
        logger.info(f"Channel reaction_settings: {channel.reaction_settings}")
        
        settings = ReactionSettings.from_dict(channel.reaction_settings)
        
        # Check if auto-boost is enabled
        if not settings.auto_boost:
            logger.info(f"Auto-boost disabled for channel {channel.id}")
            return
        
        # Validate settings
        is_valid, error_msg = settings.validate()
        if not is_valid:
            logger.error(f"Invalid reaction settings: {error_msg}")
            await self.logger.log_error(
                channel.id, post.message_id,
                'invalid_settings',
                {'error': error_msg}
            )
            return
        
        # Requirement 3.7: Select random emojis
        emojis = self._select_random_emojis(settings)
        logger.info(f"Selected emojis: {emojis}")
        
        # Requirement 3.3, 3.4: Loop through emojis and add reactions with delays
        reactions_added = 0
        
        for emoji in emojis:
            try:
                logger.info(f"Adding reaction {emoji} to post {post.message_id}")
                # Add reaction with retry logic
                await self._add_reaction_with_retry(
                    str(channel.channel_id), 
                    post.message_id, 
                    emoji
                )
                reactions_added += 1
                logger.info(f"Successfully added reaction {emoji}")
                
                # Requirement 6.1: Log each reaction added
                await self.logger.log_reaction_added(channel.id, post.message_id, emoji)
                
                # Requirement 3.4: Random delay before next reaction
                if reactions_added < len(emojis):  # Don't delay after last reaction
                    delay = random.uniform(settings.delay_min, settings.delay_max)
                    logger.info(f"Waiting {delay:.2f} seconds before next reaction")
                    await asyncio.sleep(delay)
                    
            except TelegramAPIError as e:
                logger.error(f"Error adding reaction {emoji}: {e}")
                # Requirement 4.3: Skip reaction after max retries and continue
                await self._handle_api_error(channel, post, emoji, e)
        
        # Requirement 3.5: Mark post as boosted
        if reactions_added > 0:
            logger.info(f"Marking post {post.message_id} as boosted with {reactions_added} reactions")
            await self._mark_as_boosted(channel.id, post.message_id, reactions_added, emojis)
            
            # Requirement 6.2: Log boost completion
            await self.logger.log_boost_completed(channel.id, post.message_id, reactions_added)
        else:
            logger.warning(f"No reactions added to post {post.message_id}")
    
    async def _is_already_boosted(self, channel_id: int, post_id: int) -> bool:
        """
        Check if post has already been boosted
        
        Args:
            channel_id: Database ID of the channel
            post_id: Telegram message ID
        
        Returns:
            True if post was already boosted, False otherwise
        
        Requirements: 3.6
        """
        result = await self.db.execute(
            select(BoostedPost).where(
                BoostedPost.channel_id == channel_id,
                BoostedPost.post_id == post_id
            )
        )
        return result.scalar_one_or_none() is not None
    
    def _select_random_emojis(self, settings: ReactionSettings) -> list[str]:
        """
        Select and shuffle emojis for natural appearance
        
        Args:
            settings: ReactionSettings with emoji list and count
        
        Returns:
            List of randomly selected and shuffled emojis
        
        Requirements: 3.7
        """
        emojis = settings.emojis.copy()
        random.shuffle(emojis)
        return emojis[:settings.reaction_count]
    
    async def _add_reaction_with_retry(self, channel_id: str, message_id: int, emoji: str) -> None:
        """
        Add reaction with exponential backoff retry
        
        Args:
            channel_id: Telegram channel ID (string format)
            message_id: Telegram message ID
            emoji: Emoji string to add as reaction
        
        Raises:
            TelegramError: If all retry attempts fail
        
        Requirements: 3.4, 4.1
        """
        for attempt in range(self.max_retries):
            try:
                # Aiogram 3.x format for reactions
                await self.bot.set_message_reaction(
                    chat_id=channel_id,
                    message_id=message_id,
                    reaction=[{"type": "emoji", "emoji": emoji}],
                    is_big=False
                )
                return
            except TelegramRetryAfter as e:
                if attempt < self.max_retries - 1:
                    # Wait for the specified retry-after duration
                    await asyncio.sleep(e.retry_after)
                else:
                    raise
    
    async def _mark_as_boosted(self, channel_id: int, post_id: int, 
                               reaction_count: int, emojis: list[str]) -> None:
        """
        Record boosted post in database
        
        Args:
            channel_id: Database ID of the channel
            post_id: Telegram message ID
            reaction_count: Number of reactions added
            emojis: List of emojis that were used
        
        Requirements: 3.5
        """
        boosted_post = BoostedPost(
            channel_id=channel_id,
            post_id=post_id,
            boost_timestamp=datetime.now(timezone.utc),
            reaction_count=reaction_count,
            emojis_used=emojis
        )
        self.db.add(boosted_post)
        await self.db.commit()
    
    async def _handle_api_error(self, channel: Channel, post: Message, 
                                emoji: str, error: Exception) -> None:
        """
        Handle Telegram API errors
        
        Args:
            channel: Channel model instance
            post: Telegram Message object
            emoji: Emoji that failed to be added
            error: Exception that was raised
        
        Requirements: 4.2, 4.3, 4.4, 4.5
        """
        if isinstance(error, TelegramForbiddenError):
            # Requirement 4.4: Log permission error and disable reaction mode
            await self.logger.log_error(
                channel.id, post.message_id,
                'permission_error',
                {'message': 'Bot is not admin in channel'}
            )
            # Disable reaction mode for this channel
            await self._disable_reaction_mode(channel)
        elif isinstance(error, TelegramRetryAfter):
            # Requirement 4.2: Log rate limit error
            await self.logger.log_error(
                channel.id, post.message_id,
                'rate_limit',
                {'retry_after': error.retry_after}
            )
        else:
            # Requirement 4.5: Log unknown errors
            await self.logger.log_error(
                channel.id, post.message_id,
                'unknown_error',
                {'error': str(error), 'emoji': emoji}
            )
    
    async def _disable_reaction_mode(self, channel: Channel) -> None:
        """
        Disable reaction mode for a channel due to permission errors
        
        Args:
            channel: Channel model instance to update
        """
        # Update mode based on current setting
        if channel.mode == 'both':
            channel.mode = 'comment'
        elif channel.mode == 'reaction':
            channel.mode = 'comment'  # Fallback to comment mode
        
        await self.db.commit()
