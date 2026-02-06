"""
Admin command handler for bot management
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from datetime import datetime, timedelta

from ..config import Config
from ..database import Database
from ..models import Channel, Statistics, Response

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handler for admin commands and interface"""
    
    def __init__(self, bot: Bot, database: Database, config: Config):
        self.bot = bot
        self.database = database
        self.config = config
    
    async def handle_start_command(self, message: Message) -> None:
        """Handle /start command"""
        user_id = message.from_user.id
        
        # Check if user is admin
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply(
                "❌ Sizda admin huquqlari yo'q.\n"
                "Bu bot faqat ro'yxatdan o'tgan adminlar uchun."
            )
            return
        
        # Show main admin menu
        await self._show_main_menu(message)
    
    async def handle_stats_command(self, message: Message) -> None:
        """Handle /stats command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        await self._show_statistics(message)
    
    async def handle_settings_command(self, message: Message) -> None:
        """Handle /settings command"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        await self._show_settings_menu(message)
    
    async def handle_callback_query(self, callback: CallbackQuery) -> None:
        """Handle callback queries from inline keyboards"""
        user_id = callback.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await callback.answer("❌ Sizda admin huquqlari yo'q.")
            return
        
        data = callback.data
        
        if data == "main_menu":
            await self._show_main_menu(callback.message, edit=True)
        elif data == "show_channels":
            await self._show_channels(callback.message, edit=True)
        elif data == "add_channel":
            await self._show_add_channel_help(callback.message, edit=True)
        elif data == "show_stats":
            await self._show_statistics(callback.message, edit=True)
        elif data == "show_settings":
            await self._show_settings_menu(callback.message, edit=True)
        elif data.startswith("channel_"):
            channel_id = int(data.split("_")[1])
            await self._show_channel_details(callback.message, channel_id, edit=True)
        elif data.startswith("toggle_ai_"):
            channel_id = int(data.split("_")[2])
            await self._toggle_ai(callback.message, channel_id)
        
        await callback.answer()
    
    async def _show_main_menu(self, message: Message, edit: bool = False) -> None:
        """Show main admin menu"""
        text = (
            "🤖 <b>Telegram AI Bot - Admin Panel</b>\n\n"
            "Botni boshqarish uchun quyidagi tugmalardan foydalaning:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")],
            [InlineKeyboardButton(text="📢 Kanallar", callback_data="show_channels")],
            [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
            [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="show_settings")]
        ])
        
        if edit and message:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply(text, reply_markup=keyboard)
    
    async def _show_channels(self, message: Message, edit: bool = False) -> None:
        """Show list of configured channels"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.is_active == True))
            channels = result.scalars().all()
        finally:
            await session.close()
        
        if not channels:
            text = (
                "📢 <b>Kanallar</b>\n\n"
                "Hozircha hech qanday kanal ulanmagan.\n"
                "Kanal qo'shish uchun 'Kanal qo'shish' tugmasini bosing."
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu")]
            ])
        else:
            text = "📢 <b>Ulangan kanallar:</b>\n\n"
            keyboard_buttons = []
            
            for channel in channels:
                status = "🟢" if channel.ai_enabled else "🔴"
                text += f"{status} {channel.channel_title}\n"
                text += f"   ID: <code>{channel.channel_id}</code>\n"
                text += f"   AI: {'Yoqilgan' if channel.ai_enabled else 'Ochirilgan'}\n\n"
                
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"⚙️ {channel.channel_title[:20]}...",
                        callback_data=f"channel_{channel.id}"
                    )
                ])
            
            keyboard_buttons.extend([
                [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu")]
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        if edit and message:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply(text, reply_markup=keyboard)
    
    async def _show_add_channel_help(self, message: Message, edit: bool = False) -> None:
        """Show instructions for adding a channel"""
        text = (
            "➕ <b>Kanal qo'shish</b>\n\n"
            "<b>Qadamlar:</b>\n"
            "1. Botni kanalingizga admin qilib qo'shing\n"
            "2. Kanal uchun discussion group yarating\n"
            "3. Botni discussion groupga ham qo'shing\n"
            "4. Discussion groupda /setup buyrug'ini yuboring\n\n"
            "<b>Eslatma:</b> Bot faqat discussion group xabarlarini kuzatadi."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_channels")]
        ])
        
        if edit and message:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply(text, reply_markup=keyboard)
    
    async def _show_statistics(self, message: Message, edit: bool = False) -> None:
        """Show bot statistics"""
        session = await self.database.get_session()
        try:
            # Get today's stats
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            week_ago = today - timedelta(days=7)
            
            # Today's responses
            today_responses = await session.execute(
                select(func.count(Response.id))
                .where(func.date(Response.created_at) == today)
            )
            today_count = today_responses.scalar() or 0
            
            # Yesterday's responses
            yesterday_responses = await session.execute(
                select(func.count(Response.id))
                .where(func.date(Response.created_at) == yesterday)
            )
            yesterday_count = yesterday_responses.scalar() or 0
            
            # This week's responses
            week_responses = await session.execute(
                select(func.count(Response.id))
                .where(func.date(Response.created_at) >= week_ago)
            )
            week_count = week_responses.scalar() or 0
            
            # Total channels
            total_channels = await session.execute(
                select(func.count(Channel.id)).where(Channel.is_active == True)
            )
            channels_count = total_channels.scalar() or 0
        finally:
            await session.close()
        
        text = (
            "📊 <b>Bot Statistikasi</b>\n\n"
            f"📢 <b>Kanallar:</b> {channels_count} ta\n\n"
            f"📈 <b>Javoblar:</b>\n"
            f"   • Bugun: {today_count} ta\n"
            f"   • Kecha: {yesterday_count} ta\n"
            f"   • Bu hafta: {week_count} ta\n\n"
            f"🕐 <b>Oxirgi yangilanish:</b> {datetime.now().strftime('%H:%M')}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="show_stats")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu")]
        ])
        
        if edit and message:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply(text, reply_markup=keyboard)
    
    async def _show_settings_menu(self, message: Message, edit: bool = False) -> None:
        """Show settings menu"""
        text = (
            "⚙️ <b>Sozlamalar</b>\n\n"
            f"🤖 <b>AI Provider:</b> {self.config.DEFAULT_AI_PROVIDER}\n"
            f"📝 <b>Max javob uzunligi:</b> {self.config.MAX_RESPONSE_LENGTH}\n"
            f"⏱ <b>Rate limit:</b> {self.config.RATE_LIMIT_MINUTES} daqiqa\n"
            f"📊 <b>Kunlik limit:</b> {self.config.DAILY_RESPONSE_LIMIT}\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu")]
        ])
        
        if edit and message:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply(text, reply_markup=keyboard)
    
    async def _show_channel_details(self, message: Message, channel_id: int, edit: bool = False) -> None:
        """Show detailed channel information"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one_or_none()
            
            if not channel:
                await message.reply("❌ Kanal topilmadi.")
                return
            
            ai_status = "🟢 Yoqilgan" if channel.ai_enabled else "🔴 O'chirilgan"
            
            text = (
                f"📢 <b>{channel.channel_title}</b>\n\n"
                f"🆔 <b>ID:</b> <code>{channel.channel_id}</code>\n"
                f"💬 <b>Discussion Group:</b> <code>{channel.discussion_group_id or 'Yoq'}</code>\n"
                f"🤖 <b>AI:</b> {ai_status}\n"
                f"🔧 <b>Provider:</b> {channel.ai_provider}\n"
                f"📊 <b>Kunlik limit:</b> {channel.daily_limit}\n"
                f"⏱ <b>Rate limit:</b> {channel.rate_limit_minutes} daqiqa\n"
                f"📝 <b>Trigger so'zlar:</b> {len(channel.trigger_words)} ta\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🤖 AI {'Ochirish' if channel.ai_enabled else 'Yoqish'}",
                    callback_data=f"toggle_ai_{channel.id}"
                )],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_channels")]
            ])
            
            if edit and message:
                await message.edit_text(text, reply_markup=keyboard)
            else:
                await message.reply(text, reply_markup=keyboard)
        finally:
            await session.close()
    
    async def _toggle_ai(self, message: Message, channel_id: int) -> None:
        """Toggle AI for a channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one_or_none()
            
            if not channel:
                await message.reply("❌ Kanal topilmadi.")
                return
            
            channel.ai_enabled = not channel.ai_enabled
            await session.commit()
            
            status = "yoqildi" if channel.ai_enabled else "ochirildi"
            await message.reply(f"✅ {channel.channel_title} uchun AI {status}.")
            
            # Refresh channel details
            await self._show_channel_details(message, channel_id, edit=True)
        finally:
            await session.close()