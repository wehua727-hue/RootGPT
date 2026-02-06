"""
Channel management service for handling channel operations
"""

import logging
from typing import Optional, List
from aiogram import Bot
from aiogram.types import Chat, ChatMember
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from sqlalchemy import select

from ..config import Config
from ..database import Database
from ..models import Channel

logger = logging.getLogger(__name__)


class ChannelManager:
    """Service for managing channel operations and permissions"""
    
    def __init__(self, bot: Bot, database: Database, config: Config):
        self.bot = bot
        self.database = database
        self.config = config
    
    async def verify_channel_permissions(self, channel_id: int, user_id: int) -> bool:
        """Verify if user has admin permissions in the channel"""
        try:
            # Get bot's permissions in the channel
            bot_member = await self.bot.get_chat_member(chat_id=channel_id, user_id=self.bot.id)
            
            # Check if bot is admin
            if bot_member.status not in ['administrator', 'creator']:
                logger.warning(f"Bot is not admin in channel {channel_id}")
                return False
            
            # Get user's permissions in the channel
            user_member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            
            # Check if user is admin or creator
            if user_member.status not in ['administrator', 'creator']:
                logger.warning(f"User {user_id} is not admin in channel {channel_id}")
                return False
            
            return True
            
        except (TelegramBadRequest, TelegramAPIError) as e:
            logger.error(f"Error checking permissions for channel {channel_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking permissions: {e}")
            return False
    
    async def get_channel_info(self, channel_id: int) -> Optional[Chat]:
        """Get channel information"""
        try:
            chat = await self.bot.get_chat(chat_id=channel_id)
            return chat
        except (TelegramBadRequest, TelegramAPIError) as e:
            logger.error(f"Error getting channel info for {channel_id}: {e}")
            return None
    
    async def detect_discussion_group(self, channel_id: int) -> Optional[int]:
        """Detect linked discussion group for a channel"""
        try:
            chat = await self.bot.get_chat(chat_id=channel_id)
            
            # Check if channel has linked discussion group
            if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                return chat.linked_chat_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting discussion group for channel {channel_id}: {e}")
            return None
    
    async def setup_channel(self, channel_id: int, user_id: int, channel_title: str = None) -> Optional[Channel]:
        """Setup a new channel for monitoring"""
        try:
            # Verify permissions
            if not await self.verify_channel_permissions(channel_id, user_id):
                return None
            
            # Get channel info
            chat = await self.get_channel_info(channel_id)
            if not chat:
                return None
            
            title = channel_title or chat.title or f"Channel {channel_id}"
            
            # Detect discussion group
            discussion_group_id = await self.detect_discussion_group(channel_id)
            
            # Check if channel already exists
            async with self.database.get_session() as session:
                existing = await session.execute(
                    select(Channel).where(Channel.channel_id == channel_id)
                )
                existing_channel = existing.scalar_one_or_none()
                
                if existing_channel:
                    # Update existing channel
                    existing_channel.channel_title = title
                    existing_channel.discussion_group_id = discussion_group_id
                    existing_channel.is_active = True
                    
                    # Add user to admin list if not already there
                    if user_id not in existing_channel.admin_user_ids:
                        existing_channel.admin_user_ids.append(user_id)
                    
                    await session.commit()
                    await session.refresh(existing_channel)
                    return existing_channel
                else:
                    # Create new channel
                    new_channel = Channel(
                        channel_id=channel_id,
                        channel_title=title,
                        discussion_group_id=discussion_group_id,
                        ai_enabled=True,
                        admin_user_ids=[user_id]
                    )
                    
                    session.add(new_channel)
                    await session.commit()
                    await session.refresh(new_channel)
                    return new_channel
                    
        except Exception as e:
            logger.error(f"Error setting up channel {channel_id}: {e}")
            return None
    
    async def get_user_channels(self, user_id: int) -> List[Channel]:
        """Get channels where user is admin"""
        async with self.database.get_session() as session:
            result = await session.execute(
                select(Channel).where(
                    Channel.admin_user_ids.contains([user_id]),
                    Channel.is_active == True
                )
            )
            return list(result.scalars().all())
    
    async def validate_bot_permissions(self, channel_id: int) -> dict:
        """Validate bot permissions in channel and return detailed info"""
        try:
            bot_member = await self.bot.get_chat_member(chat_id=channel_id, user_id=self.bot.id)
            
            permissions = {
                'is_admin': bot_member.status in ['administrator', 'creator'],
                'can_post_messages': False,
                'can_edit_messages': False,
                'can_delete_messages': False,
                'can_manage_chat': False,
                'status': bot_member.status
            }
            
            if hasattr(bot_member, 'can_post_messages'):
                permissions['can_post_messages'] = bot_member.can_post_messages
            if hasattr(bot_member, 'can_edit_messages'):
                permissions['can_edit_messages'] = bot_member.can_edit_messages
            if hasattr(bot_member, 'can_delete_messages'):
                permissions['can_delete_messages'] = bot_member.can_delete_messages
            if hasattr(bot_member, 'can_manage_chat'):
                permissions['can_manage_chat'] = bot_member.can_manage_chat
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error validating bot permissions for channel {channel_id}: {e}")
            return {
                'is_admin': False,
                'can_post_messages': False,
                'can_edit_messages': False,
                'can_delete_messages': False,
                'can_manage_chat': False,
                'status': 'error',
                'error': str(e)
            }
    
    async def is_user_admin_in_any_channel(self, user_id: int) -> bool:
        """Check if user is admin in any configured channel"""
        channels = await self.get_user_channels(user_id)
        return len(channels) > 0
    
    async def remove_channel(self, channel_id: int, user_id: int) -> bool:
        """Remove channel from monitoring (deactivate)"""
        try:
            async with self.database.get_session() as session:
                result = await session.execute(
                    select(Channel).where(Channel.channel_id == channel_id)
                )
                channel = result.scalar_one_or_none()
                
                if not channel:
                    return False
                
                # Check if user has permission to remove
                if user_id not in channel.admin_user_ids and user_id not in self.config.ADMIN_USER_IDS:
                    return False
                
                # Deactivate channel
                channel.is_active = False
                await session.commit()
                
                logger.info(f"Channel {channel_id} deactivated by user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error removing channel {channel_id}: {e}")
            return False