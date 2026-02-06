"""
AutoRepostService - Core service for monitoring and reposting channel content
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import RepostConfig, RepostLog, RepostStats

logger = logging.getLogger(__name__)


class AutoRepostService:
    """Service for monitoring and reposting channel content"""
    
    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session
        logger.info("AutoRepostService initialized")
    
    async def monitor_all_sources(self) -> None:
        """Check all enabled source channels for new content"""
        try:
            # Get all enabled configs
            result = await self.session.execute(
                select(RepostConfig).where(RepostConfig.is_enabled == True)
            )
            configs = result.scalars().all()
            
            if not configs:
                logger.info("No enabled repost configs found")
                return
            
            logger.info(f"Monitoring {len(configs)} source channels")
            
            # Monitor each source independently
            for config in configs:
                try:
                    await self.monitor_source(config)
                except Exception as e:
                    # Error isolation - continue with other channels
                    logger.error(f"Failed to monitor {config.source_channel_title}: {e}")
                    continue
            
            logger.info("Monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"Error in monitor_all_sources: {e}")
    
    async def monitor_source(self, config: RepostConfig) -> None:
        """Monitor a single source channel"""
        try:
            logger.info(f"Monitoring source: {config.source_channel_title}")
            
            # Update last check time
            config.last_check_at = datetime.now(timezone.utc)
            
            # Get new message IDs
            message_ids = await self.get_new_messages(config)
            
            if not message_ids:
                logger.info(f"No new messages in {config.source_channel_title}")
                await self.session.commit()
                return
            
            # Process each message
            for msg_id in message_ids:
                try:
                    # Copy message to get Message object
                    # We'll use a temporary approach - copy and immediately process
                    message = await self.bot.copy_message(
                        chat_id=config.target_channel_id,
                        from_chat_id=config.source_channel_id,
                        message_id=msg_id
                    )
                    
                    # Delete the temporary copy
                    await self.bot.delete_message(config.target_channel_id, message.message_id)
                    
                    # Now repost properly with filters and watermark
                    # We need to get the original message - use forward as workaround
                    forwarded = await self.bot.forward_message(
                        chat_id=config.target_channel_id,
                        from_chat_id=config.source_channel_id,
                        message_id=msg_id
                    )
                    
                    # Process the forwarded message
                    await self.repost_message(config, forwarded)
                    
                    # Delete the forwarded message
                    await self.bot.delete_message(config.target_channel_id, forwarded.message_id)
                    
                    # Update last processed message ID
                    config.last_processed_message_id = msg_id
                    
                except Exception as e:
                    logger.error(f"Error processing message {msg_id}: {e}")
                    continue
            
            # Update config status
            config.status = "active"
            config.last_error = None
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Error monitoring {config.source_channel_title}: {e}")
            config.status = "error"
            config.last_error = str(e)
            await self.session.commit()
    
    async def repost_message(self, config: RepostConfig, message: Message) -> bool:
        """Repost a single message to target channel"""
        content_type = "unknown"
        try:
            # Determine content type
            if message.text:
                content_type = "text"
            elif message.photo:
                content_type = "photo"
            elif message.video:
                content_type = "video"
            elif message.document:
                content_type = "document"
            elif message.audio:
                content_type = "audio"
            elif message.voice:
                content_type = "voice"
            elif message.animation:
                content_type = "animation"
            
            # Apply content filter
            if config.allowed_content_types:
                if not await self.apply_content_filter(message, config.allowed_content_types):
                    logger.info(f"Message {message.message_id} filtered out (type: {content_type})")
                    # Log as filtered
                    log = RepostLog(
                        config_id=config.id,
                        source_message_id=message.message_id,
                        content_type=content_type,
                        status="filtered"
                    )
                    self.session.add(log)
                    await self.update_statistics(config, "filtered", content_type)
                    return False
            
            # Apply delay if configured
            if config.repost_delay_seconds > 0:
                await asyncio.sleep(config.repost_delay_seconds)
            
            # Repost with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Copy message with watermark
                    sent_message = await self.copy_message_with_watermark(
                        message,
                        config.target_channel_id,
                        config.watermark_text
                    )
                    
                    # Log success
                    log = RepostLog(
                        config_id=config.id,
                        source_message_id=message.message_id,
                        target_message_id=sent_message.message_id,
                        content_type=content_type,
                        status="success"
                    )
                    self.session.add(log)
                    await self.update_statistics(config, "success", content_type)
                    
                    logger.info(f"Successfully reposted message {message.message_id} to {config.target_channel_id}")
                    return True
                    
                except TelegramAPIError as e:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
            
        except Exception as e:
            logger.error(f"Failed to repost message {message.message_id}: {e}")
            # Log failure
            log = RepostLog(
                config_id=config.id,
                source_message_id=message.message_id,
                content_type=content_type,
                status="failed",
                error_message=str(e)
            )
            self.session.add(log)
            await self.update_statistics(config, "failed", content_type)
            return False
    
    async def get_new_messages(self, config: RepostConfig) -> List[Message]:
        """Fetch new messages from source channel"""
        try:
            messages = []
            # Get chat to verify access
            chat = await self.bot.get_chat(config.source_channel_id)
            
            # Telegram doesn't have a direct "get messages after ID" API
            # We'll use a workaround: get recent messages and filter
            # Note: This is a limitation - we can only get recent messages
            # For production, consider using MTProto client for better message fetching
            
            # For now, we'll implement a simple approach:
            # Try to get messages by iterating from last_processed_message_id + 1
            last_id = config.last_processed_message_id
            
            # Try to fetch up to 100 messages after last_processed_message_id
            for offset in range(1, 101):
                try:
                    msg_id = last_id + offset
                    # Try to forward message to ourselves to check if it exists
                    # This is a workaround since aiogram doesn't have get_message
                    msg = await self.bot.forward_message(
                        chat_id=config.target_channel_id,
                        from_chat_id=config.source_channel_id,
                        message_id=msg_id
                    )
                    # Delete the forwarded message immediately
                    await self.bot.delete_message(config.target_channel_id, msg.message_id)
                    
                    # If we got here, message exists - fetch it properly
                    # Since we can't get message directly, we'll use copy_message approach
                    messages.append(msg_id)
                    
                except TelegramAPIError:
                    # Message doesn't exist or we've reached the end
                    break
            
            logger.info(f"Found {len(messages)} new messages in {chat.title}")
            return messages
            
        except TelegramAPIError as e:
            logger.error(f"Failed to get messages from {config.source_channel_id}: {e}")
            config.status = "error"
            config.last_error = str(e)
            await self.session.commit()
            return []
    
    async def apply_content_filter(self, message: Message, allowed_types: List[str]) -> bool:
        """Check if message matches content filter"""
        # If no filter configured, allow all
        if not allowed_types:
            return True
        
        # Determine message content type
        content_type = None
        if message.text:
            content_type = "text"
        elif message.photo:
            content_type = "photo"
        elif message.video:
            content_type = "video"
        elif message.document:
            content_type = "document"
        elif message.audio:
            content_type = "audio"
        elif message.voice:
            content_type = "voice"
        elif message.animation:
            content_type = "animation"
        elif message.sticker:
            content_type = "sticker"
        elif message.poll:
            content_type = "poll"
        elif message.location:
            content_type = "location"
        else:
            content_type = "unknown"
        
        # Check if content type is allowed
        return content_type in allowed_types
    
    async def copy_message_with_watermark(
        self,
        message: Message,
        target_channel_id: int,
        watermark: Optional[str]
    ) -> Message:
        """Copy message to target with optional watermark"""
        try:
            # Prepare caption/text with watermark
            original_text = message.caption or message.text or ""
            if watermark:
                new_text = f"{original_text}\n\n{watermark}" if original_text else watermark
            else:
                new_text = original_text
            
            # Copy message based on type
            if message.photo:
                return await self.bot.send_photo(
                    chat_id=target_channel_id,
                    photo=message.photo[-1].file_id,
                    caption=new_text[:1024] if new_text else None
                )
            elif message.video:
                return await self.bot.send_video(
                    chat_id=target_channel_id,
                    video=message.video.file_id,
                    caption=new_text[:1024] if new_text else None
                )
            elif message.document:
                return await self.bot.send_document(
                    chat_id=target_channel_id,
                    document=message.document.file_id,
                    caption=new_text[:1024] if new_text else None
                )
            elif message.audio:
                return await self.bot.send_audio(
                    chat_id=target_channel_id,
                    audio=message.audio.file_id,
                    caption=new_text[:1024] if new_text else None
                )
            elif message.voice:
                return await self.bot.send_voice(
                    chat_id=target_channel_id,
                    voice=message.voice.file_id,
                    caption=new_text[:1024] if new_text else None
                )
            elif message.animation:
                return await self.bot.send_animation(
                    chat_id=target_channel_id,
                    animation=message.animation.file_id,
                    caption=new_text[:1024] if new_text else None
                )
            elif message.text:
                return await self.bot.send_message(
                    chat_id=target_channel_id,
                    text=new_text[:4096] if new_text else "..."
                )
            else:
                # For other types, use copy_message
                return await self.bot.copy_message(
                    chat_id=target_channel_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
                
        except TelegramAPIError as e:
            logger.error(f"Failed to copy message: {e}")
            raise
    
    async def update_statistics(
        self,
        config: RepostConfig,
        status: str,
        content_type: str
    ) -> None:
        """Update repost statistics"""
        try:
            # Get or create stats record
            result = await self.session.execute(
                select(RepostStats).where(RepostStats.config_id == config.id)
            )
            stats = result.scalar_one_or_none()
            
            if not stats:
                stats = RepostStats(config_id=config.id)
                self.session.add(stats)
            
            # Update counters
            stats.total_reposts += 1
            if status == "success":
                stats.successful_reposts += 1
                stats.last_repost_at = datetime.now(timezone.utc)
            elif status == "failed":
                stats.failed_reposts += 1
            elif status == "filtered":
                stats.filtered_posts += 1
            
            # Update content type counts
            if not stats.content_type_counts:
                stats.content_type_counts = {}
            
            counts = stats.content_type_counts
            counts[content_type] = counts.get(content_type, 0) + 1
            stats.content_type_counts = counts
            
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            await self.session.rollback()
