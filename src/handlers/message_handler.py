"""
Message handler for processing comments from discussion groups
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select

from ..config import Config
from ..database import Database
from ..models import Channel, Comment, CommentCategory
from ..services.comment_monitor import CommentMonitor
from ..services.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handler for processing messages from discussion groups"""
    
    def __init__(self, bot: Bot, database: Database, config: Config):
        self.bot = bot
        self.database = database
        self.config = config
        self.comment_monitor = CommentMonitor(bot, database, config)
        self.response_generator = ResponseGenerator(bot, database, config)
    
    async def handle_message(self, message: Message) -> None:
        """Handle incoming messages"""
        try:
            # Debug: log all messages
            logger.info(f"Received message from chat {message.chat.id}: {message.text}")
            
            # Skip if no text
            if not message.text:
                logger.info("Skipping message: no text")
                return
            
            # Skip bot messages
            if message.from_user and message.from_user.is_bot:
                logger.info("Skipping message: from bot")
                return
            
            # Check if message is from a monitored discussion group
            chat_id = message.chat.id
            logger.info(f"Looking for channel with discussion_group_id: {chat_id}")
            
            channel = await self._get_channel_by_discussion_group(chat_id)
            
            if not channel:
                logger.info(f"No channel found for discussion group {chat_id}")
                # Check if this is a setup command in a new group
                if message.text.startswith('/setup'):
                    logger.info("Processing setup command")
                    await self._handle_setup_command(message)
                else:
                    logger.info("Not a setup command, ignoring")
                return
            
            logger.info(f"Found channel {channel.id} for discussion group {chat_id}")
            
            # Process the comment
            await self.comment_monitor.process_comment(message, channel)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _get_channel_by_discussion_group(self, discussion_group_id: int) -> Optional[Channel]:
        """Get channel by discussion group ID"""
        session = await self.database.get_session()
        try:
            result = await session.execute(
                select(Channel).where(
                    Channel.discussion_group_id == discussion_group_id,
                    Channel.is_active == True
                )
            )
            return result.scalar_one_or_none()
        finally:
            await session.close()
    
    async def _handle_setup_command(self, message: Message) -> None:
        """Handle /setup command for linking discussion group to channel"""
        user_id = message.from_user.id
        
        # Check if user is admin
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply(
                "❌ Faqat adminlar kanal sozlay oladi.\n"
                "Agar siz admin bo'lsangiz, bot konfiguratsiyasida user ID ni qo'shing."
            )
            return
        
        chat_id = message.chat.id
        chat_title = message.chat.title or "Noma'lum group"
        
        # Check if this group is already linked
        existing_channel = await self._get_channel_by_discussion_group(chat_id)
        if existing_channel:
            await message.reply(
                f"✅ Bu group allaqachon '{existing_channel.channel_title}' kanaliga ulangan."
            )
            return
        
        # For now, we'll create a basic channel entry
        # In a full implementation, you'd want to verify the linked channel
        session = await self.database.get_session()
        try:
            new_channel = Channel(
                channel_id=0,  # Will be updated when we detect the actual channel
                channel_title=f"Channel for {chat_title}",
                discussion_group_id=chat_id,
                ai_enabled=True,
                admin_user_ids=[user_id]
            )
            
            session.add(new_channel)
            await session.commit()
            
            await message.reply(
                f"✅ Discussion group '{chat_title}' muvaffaqiyatli ulandi!\n\n"
                f"📋 <b>Keyingi qadamlar:</b>\n"
                f"1. Botni asosiy kanalingizga admin qilib qo'shing\n"
                f"2. /start buyrug'i orqali admin paneldan sozlamalarni o'zgartiring\n"
                f"3. AI javoblarini yoqing va trigger so'zlarni sozlang\n\n"
                f"🤖 Bot endi bu groupdagi har qanday komentga javob beradi!"
            )
        finally:
            await session.close()