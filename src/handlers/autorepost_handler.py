"""
Auto-repost command handler for managing channel reposting
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Config
from src.models import RepostConfig, RepostStats
from src.services.auto_repost_service import AutoRepostService

logger = logging.getLogger(__name__)


class AutoRepostHandler:
    """Handler for auto-repost commands"""
    
    def __init__(self, bot: Bot, config: Config):
        self.bot = bot
        self.config = config
    
    async def handle_autorepost_add(self, message: Message, session: AsyncSession) -> None:
        """Handle /autorepost add command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        # Parse command: /autorepost add <source_channel> <target_channel>
        parts = message.text.split()
        
        if len(parts) < 3:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format:\n"
                "/autorepost add <source_kanal> <target_kanal>\n\n"
                "Misol:\n"
                "/autorepost add @prikollar_vidyolar_videolar_klip @my_channel\n"
                "yoki\n"
                "/autorepost add -1001234567890 -1009876543210"
            )
            return
        
        source_input = parts[2]
        target_input = parts[3] if len(parts) > 3 else None
        
        if not target_input:
            await message.reply("❌ Target kanalini kiriting!")
            return
        
        try:
            # Get source channel info
            if source_input.startswith('@'):
                source_chat = await self.bot.get_chat(source_input)
            else:
                source_chat = await self.bot.get_chat(int(source_input))
            
            # Get target channel info
            if target_input.startswith('@'):
                target_chat = await self.bot.get_chat(target_input)
            else:
                target_chat = await self.bot.get_chat(int(target_input))
            
            # Check if config already exists
            result = await session.execute(
                select(RepostConfig).where(RepostConfig.source_channel_id == source_chat.id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await message.reply(
                    f"❌ Bu kanal allaqachon qo'shilgan!\n\n"
                    f"Source: {existing.source_channel_title}\n"
                    f"Target: {existing.target_channel_title}\n"
                    f"Status: {'✅ Yoqilgan' if existing.is_enabled else '❌ O\'chirilgan'}"
                )
                return
            
            # Create new config
            config = RepostConfig(
                source_channel_id=source_chat.id,
                source_channel_title=source_chat.title or source_chat.username or str(source_chat.id),
                source_channel_username=source_chat.username,
                target_channel_id=target_chat.id,
                target_channel_title=target_chat.title or target_chat.username or str(target_chat.id),
                is_enabled=True,
                status='active'
            )
            session.add(config)
            await session.flush()  # Flush to get config.id
            
            # Create initial stats
            stats = RepostStats(config_id=config.id)
            session.add(stats)
            
            await session.commit()
            
            await message.reply(
                f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
                f"📥 Source: {config.source_channel_title}\n"
                f"📤 Target: {config.target_channel_title}\n"
                f"⏱ Interval: {config.check_interval_seconds}s\n"
                f"🔄 Status: Yoqilgan\n\n"
                f"Konfiguratsiya uchun: /autorepost config {source_chat.id}"
            )
            
        except TelegramAPIError as e:
            await message.reply(f"❌ Xatolik: {e}")
        except Exception as e:
            logger.error(f"Error adding repost config: {e}")
            await message.reply(f"❌ Xatolik yuz berdi: {e}")
    
    async def handle_autorepost_list(self, message: Message, session: AsyncSession) -> None:
        """Handle /autorepost list command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        try:
            # Get all configs
            result = await session.execute(select(RepostConfig))
            configs = result.scalars().all()
            
            if not configs:
                await message.reply("📋 Hech qanday kanal qo'shilmagan.")
                return
            
            # Build response
            response = "📋 Auto-repost kanallari:\n\n"
            
            for config in configs:
                status_emoji = "✅" if config.is_enabled else "❌"
                status_text = "Yoqilgan" if config.is_enabled else "O'chirilgan"
                
                # Get stats
                stats_result = await session.execute(
                    select(RepostStats).where(RepostStats.config_id == config.id)
                )
                stats = stats_result.scalar_one_or_none()
                
                total = stats.total_reposts if stats else 0
                
                response += (
                    f"{status_emoji} **{config.source_channel_title}**\n"
                    f"   → {config.target_channel_title}\n"
                    f"   📊 Jami: {total} ta post\n"
                    f"   🔄 Status: {status_text}\n"
                    f"   ID: `{config.source_channel_id}`\n\n"
                )
            
            response += "\n💡 Konfiguratsiya: /autorepost config <channel_id>"
            
            await message.reply(response, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error listing repost configs: {e}")
            await message.reply(f"❌ Xatolik: {e}")
    
    async def handle_autorepost_remove(self, message: Message, session: AsyncSession) -> None:
        """Handle /autorepost remove command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        parts = message.text.split()
        
        if len(parts) < 3:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format:\n"
                "/autorepost remove <channel_id>\n\n"
                "Misol:\n"
                "/autorepost remove -1001234567890"
            )
            return
        
        channel_input = parts[2]
        
        try:
            # Parse channel ID
            if channel_input.startswith('@'):
                chat = await self.bot.get_chat(channel_input)
                channel_id = chat.id
            else:
                channel_id = int(channel_input)
            
            # Find config
            result = await session.execute(
                select(RepostConfig).where(RepostConfig.source_channel_id == channel_id)
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await message.reply("❌ Kanal topilmadi!")
                return
            
            # Delete config (cascade deletes logs and stats)
            await session.delete(config)
            await session.commit()
            
            await message.reply(
                f"✅ Kanal o'chirildi!\n\n"
                f"Source: {config.source_channel_title}\n"
                f"Target: {config.target_channel_title}"
            )
            
        except Exception as e:
            logger.error(f"Error removing repost config: {e}")
            await message.reply(f"❌ Xatolik: {e}")
    
    async def handle_autorepost_enable(self, message: Message, session: AsyncSession) -> None:
        """Handle /autorepost enable command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        parts = message.text.split()
        
        if len(parts) < 3:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format:\n"
                "/autorepost enable <channel_id>"
            )
            return
        
        channel_input = parts[2]
        
        try:
            # Parse channel ID
            if channel_input.startswith('@'):
                chat = await self.bot.get_chat(channel_input)
                channel_id = chat.id
            else:
                channel_id = int(channel_input)
            
            # Find config
            result = await session.execute(
                select(RepostConfig).where(RepostConfig.source_channel_id == channel_id)
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await message.reply("❌ Kanal topilmadi!")
                return
            
            config.is_enabled = True
            config.status = 'active'
            await session.commit()
            
            await message.reply(
                f"✅ Kanal yoqildi!\n\n"
                f"Source: {config.source_channel_title}\n"
                f"Target: {config.target_channel_title}"
            )
            
        except Exception as e:
            logger.error(f"Error enabling repost config: {e}")
            await message.reply(f"❌ Xatolik: {e}")
    
    async def handle_autorepost_disable(self, message: Message, session: AsyncSession) -> None:
        """Handle /autorepost disable command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        parts = message.text.split()
        
        if len(parts) < 3:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format:\n"
                "/autorepost disable <channel_id>"
            )
            return
        
        channel_input = parts[2]
        
        try:
            # Parse channel ID
            if channel_input.startswith('@'):
                chat = await self.bot.get_chat(channel_input)
                channel_id = chat.id
            else:
                channel_id = int(channel_input)
            
            # Find config
            result = await session.execute(
                select(RepostConfig).where(RepostConfig.source_channel_id == channel_id)
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await message.reply("❌ Kanal topilmadi!")
                return
            
            config.is_enabled = False
            config.status = 'disabled'
            await session.commit()
            
            await message.reply(
                f"✅ Kanal o'chirildi!\n\n"
                f"Source: {config.source_channel_title}\n"
                f"Target: {config.target_channel_title}"
            )
            
        except Exception as e:
            logger.error(f"Error disabling repost config: {e}")
            await message.reply(f"❌ Xatolik: {e}")
    
    async def handle_autorepost_stats(self, message: Message, session: AsyncSession) -> None:
        """Handle /autorepost stats command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        parts = message.text.split()
        channel_id = None
        
        if len(parts) >= 3:
            channel_input = parts[2]
            try:
                if channel_input.startswith('@'):
                    chat = await self.bot.get_chat(channel_input)
                    channel_id = chat.id
                else:
                    channel_id = int(channel_input)
            except:
                pass
        
        try:
            if channel_id:
                # Get stats for specific channel
                result = await session.execute(
                    select(RepostConfig).where(RepostConfig.source_channel_id == channel_id)
                )
                config = result.scalar_one_or_none()
                
                if not config:
                    await message.reply("❌ Kanal topilmadi!")
                    return
                
                stats_result = await session.execute(
                    select(RepostStats).where(RepostStats.config_id == config.id)
                )
                stats = stats_result.scalar_one_or_none()
                
                if not stats:
                    await message.reply("📊 Statistika topilmadi.")
                    return
                
                response = (
                    f"📊 **{config.source_channel_title}** statistikasi:\n\n"
                    f"📥 Jami: {stats.total_reposts}\n"
                    f"✅ Muvaffaqiyatli: {stats.successful_reposts}\n"
                    f"❌ Xato: {stats.failed_reposts}\n"
                    f"🚫 Filtrlangan: {stats.filtered_posts}\n\n"
                )
                
                if stats.content_type_counts:
                    response += "📋 Kontent turlari:\n"
                    for content_type, count in stats.content_type_counts.items():
                        response += f"   • {content_type}: {count}\n"
                
                if stats.last_repost_at:
                    response += f"\n🕐 Oxirgi repost: {stats.last_repost_at.strftime('%Y-%m-%d %H:%M')}"
                
                await message.reply(response, parse_mode="Markdown")
                
            else:
                # Get stats for all channels
                result = await session.execute(select(RepostConfig))
                configs = result.scalars().all()
                
                if not configs:
                    await message.reply("📊 Hech qanday kanal qo'shilmagan.")
                    return
                
                response = "📊 Barcha kanallar statistikasi:\n\n"
                
                for config in configs:
                    stats_result = await session.execute(
                        select(RepostStats).where(RepostStats.config_id == config.id)
                    )
                    stats = stats_result.scalar_one_or_none()
                    
                    if stats:
                        response += (
                            f"**{config.source_channel_title}**\n"
                            f"   Jami: {stats.total_reposts} | "
                            f"✅ {stats.successful_reposts} | "
                            f"❌ {stats.failed_reposts}\n\n"
                        )
                
                await message.reply(response, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Error getting repost stats: {e}")
            await message.reply(f"❌ Xatolik: {e}")
