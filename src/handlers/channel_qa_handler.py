"""
Channel Q&A Handler - Manages channels for Q&A functionality
"""

import logging
from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select

from src.config import Config
from src.database import Database
from src.models import Channel

logger = logging.getLogger(__name__)


class ChannelQAHandler:
    """Handler for channel Q&A management"""
    
    def __init__(self, bot: Bot, database: Database, config: Config):
        self.bot = bot
        self.database = database
        self.config = config
    
    async def handle_addchannel_command(self, message: Message) -> None:
        """Handle /addchannel command - add channel by ID"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        # Parse command: /addchannel <channel_id>
        parts = message.text.split()
        
        if len(parts) < 2:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format:\n"
                "<code>/addchannel -1001234567890</code>\n\n"
                "Kanal ID ni olish uchun:\n"
                "1. Kanalga post qo'shing\n"
                "2. Postni forward qiling @userinfobot ga\n"
                "3. Bot sizga kanal ID ni beradi"
            )
            return
        
        try:
            channel_id = int(parts[1])
        except ValueError:
            await message.reply("❌ Kanal ID raqam bo'lishi kerak!")
            return
        
        # Get channel info from Telegram
        try:
            chat = await self.bot.get_chat(channel_id)
            channel_title = chat.title or chat.username or str(channel_id)
        except Exception as e:
            await message.reply(
                f"❌ Kanal topilmadi!\n\n"
                f"Xatolik: {e}\n\n"
                f"Tekshiring:\n"
                f"1. Bot kanalga admin qilib qo'shilganmi?\n"
                f"2. Kanal ID to'g'rimi? (masalan: -1001234567890)"
            )
            return
        
        # Check if channel already exists
        session = await self.database.get_session()
        try:
            result = await session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await message.reply(
                    f"✅ Kanal allaqachon qo'shilgan!\n\n"
                    f"📢 Kanal: {existing.channel_title}\n"
                    f"🆔 ID: <code>{existing.channel_id}</code>\n"
                    f"📊 Status: {'✅ Faol' if existing.is_active else '❌ Nofaol'}\n"
                    f"🤖 Mode: {existing.mode}\n\n"
                    f"Endi kanalga savol yozing va bot javob beradi!"
                )
                return
            
            # Create new channel
            channel = Channel(
                channel_id=channel_id,
                channel_title=channel_title,
                is_active=True,
                mode='comment'  # Default mode for Q&A
            )
            
            session.add(channel)
            await session.commit()
            await session.refresh(channel)
            
            await message.reply(
                f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
                f"📢 Kanal: {channel_title}\n"
                f"🆔 ID: <code>{channel_id}</code>\n"
                f"🤖 Mode: Q&A (har bir postga javob beradi)\n\n"
                f"🎉 Endi kanalga savol yozing va bot avtomatik javob beradi!\n\n"
                f"💡 Maslahat:\n"
                f"• Texnik savollar uchun: Python, JavaScript, React, Django va boshqalar\n"
                f"• Oddiy savollar uchun: har qanday mavzu\n"
                f"• Bot har bir postga javob beradi!"
            )
            
            logger.info(f"Channel added: {channel_title} (ID: {channel_id})")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error adding channel: {e}")
            await message.reply(f"❌ Xatolik yuz berdi: {e}")
        finally:
            await session.close()
    
    async def handle_listchannels_command(self, message: Message) -> None:
        """Handle /listchannels command - list all channels"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel))
            channels = result.scalars().all()
            
            if not channels:
                await message.reply("📋 Hech qanday kanal qo'shilmagan.")
                return
            
            response = "📋 Qo'shilgan kanallar:\n\n"
            
            for channel in channels:
                status_emoji = "✅" if channel.is_active else "❌"
                response += (
                    f"{status_emoji} **{channel.channel_title}**\n"
                    f"   🆔 ID: <code>{channel.channel_id}</code>\n"
                    f"   🤖 Mode: {channel.mode}\n"
                    f"   📊 Status: {'Faol' if channel.is_active else 'Nofaol'}\n\n"
                )
            
            response += "\n💡 Kanal qo'shish: /addchannel <channel_id>"
            
            await message.reply(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error listing channels: {e}")
            await message.reply(f"❌ Xatolik: {e}")
        finally:
            await session.close()
    
    async def handle_removechannel_command(self, message: Message) -> None:
        """Handle /removechannel command - remove channel"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        parts = message.text.split()
        
        if len(parts) < 2:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format:\n"
                "<code>/removechannel -1001234567890</code>"
            )
            return
        
        try:
            channel_id = int(parts[1])
        except ValueError:
            await message.reply("❌ Kanal ID raqam bo'lishi kerak!")
            return
        
        session = await self.database.get_session()
        try:
            result = await session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            )
            channel = result.scalar_one_or_none()
            
            if not channel:
                await message.reply("❌ Kanal topilmadi!")
                return
            
            channel_title = channel.channel_title
            await session.delete(channel)
            await session.commit()
            
            await message.reply(
                f"✅ Kanal o'chirildi!\n\n"
                f"📢 Kanal: {channel_title}\n"
                f"🆔 ID: <code>{channel_id}</code>"
            )
            
            logger.info(f"Channel removed: {channel_title} (ID: {channel_id})")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error removing channel: {e}")
            await message.reply(f"❌ Xatolik: {e}")
        finally:
            await session.close()
