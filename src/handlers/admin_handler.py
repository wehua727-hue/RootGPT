"""
Admin command handler for bot management
"""

import logging
import asyncio
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
    
    async def handle_boost_command(self, message: Message) -> None:
        """Handle /boost command - manually boost a post"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        # Parse command: /boost <channel_id> <message_id> OR /boost <post_link>
        parts = message.text.split()
        
        if len(parts) == 2:
            # Post link format: /boost https://t.me/channel/123
            post_link = parts[1]
            
            # Parse link
            if 't.me/' in post_link:
                try:
                    # Extract channel and message ID from link
                    # Format 1: https://t.me/username/123
                    # Format 2: https://t.me/c/1234567890/123
                    
                    link_parts = post_link.split('/')
                    
                    if '/c/' in post_link:
                        # Private channel: https://t.me/c/1234567890/123
                        channel_id_str = link_parts[-2]
                        post_id = int(link_parts[-1])
                        channel_id = int(f"-100{channel_id_str}")
                    else:
                        # Public channel: https://t.me/username/123
                        username = link_parts[-2]
                        post_id = int(link_parts[-1])
                        
                        # Get channel info by username
                        try:
                            chat = await self.bot.get_chat(f"@{username}")
                            channel_id = chat.id
                        except Exception as e:
                            await message.reply(f"❌ Kanal topilmadi: @{username}\n\nXatolik: {e}")
                            return
                    
                except Exception as e:
                    await message.reply(f"❌ Link noto'g'ri formatda!\n\nXatolik: {e}")
                    return
            else:
                await message.reply(
                    "❌ Noto'g'ri format!\n\n"
                    "To'g'ri formatlar:\n"
                    "1. <code>/boost https://t.me/channel/123</code>\n"
                    "2. <code>/boost -1001234567890 123</code>"
                )
                return
        
        elif len(parts) == 3:
            # Manual format: /boost <channel_id> <message_id>
            try:
                channel_id = int(parts[1])
                post_id = int(parts[2])
            except ValueError:
                await message.reply("❌ Kanal ID va Post ID raqam bo'lishi kerak!")
                return
        else:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri formatlar:\n"
                "1. <code>/boost https://t.me/channel/123</code>\n"
                "2. <code>/boost -1001234567890 123</code>\n\n"
                "Bu yerda:\n"
                "• Post linkini to'g'ridan-to'g'ri yuboring\n"
                "• Yoki kanal ID va post ID ni alohida kiriting"
            )
            return
        
        # Get channel from database
        session = await self.database.get_session()
        try:
            from sqlalchemy import select
            result = await session.execute(
                select(Channel).where(
                    Channel.channel_id == channel_id,
                    Channel.is_active == True
                )
            )
            channel = result.scalar_one_or_none()
            
            if not channel:
                # Try to find channel by ID and update channel_id
                result = await session.execute(select(Channel).where(Channel.is_active == True))
                all_channels = result.scalars().all()
                
                if all_channels:
                    await message.reply(
                        f"❌ Kanal topilmadi!\n\n"
                        f"Mavjud kanallar:\n" +
                        "\n".join([f"• {ch.channel_title} (ID: {ch.channel_id})" for ch in all_channels]) +
                        f"\n\nAgar kanal ID noto'g'ri bo'lsa, /fixchannel {channel_id} buyrug'ini ishlating."
                    )
                else:
                    await message.reply(
                        f"❌ Kanal topilmadi!\n\n"
                        f"Kanal ID: <code>{channel_id}</code>\n\n"
                        f"Avval kanalni qo'shing: /start"
                    )
                return
            
            if not channel.reaction_settings:
                await message.reply(
                    f"❌ Kanal uchun reaksiya sozlamalari yo'q!\n\n"
                    f"Avval reaksiya sozlamalarini o'rnating:\n"
                    f"/start → Kanallar → {channel.channel_title} → Reaksiya sozlamalari"
                )
                return
            
            # Try to get the message
            try:
                msg = await self.bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=channel_id,
                    message_id=post_id
                )
                await msg.delete()
            except Exception:
                pass  # Message might not be forwardable
            
            # Add reactions
            from ..services.reaction_boost_service import ReactionBoostService
            from ..models.reaction_settings import ReactionSettings
            
            settings = ReactionSettings.from_dict(channel.reaction_settings)
            
            # Create a fake Message object for boost_post
            class FakeMessage:
                def __init__(self, chat_id, message_id):
                    self.chat = type('obj', (object,), {'id': chat_id})()
                    self.message_id = message_id
            
            fake_msg = FakeMessage(channel_id, post_id)
            
            # Initialize service
            reaction_service = ReactionBoostService(self.bot, session)
            
            await message.reply(
                f"⏳ Reaksiyalar qo'shilmoqda...\n\n"
                f"Kanal: {channel.channel_title}\n"
                f"Post ID: {post_id}\n"
                f"Emojilar: {' '.join(settings.emojis[:settings.reaction_count])}"
            )
            
            # Boost the post
            await reaction_service.boost_post(channel, fake_msg, force=True)
            
            await message.reply(
                f"✅ Reaksiyalar qo'shildi!\n\n"
                f"Kanal: {channel.channel_title}\n"
                f"Post ID: {post_id}"
            )
            
        except Exception as e:
            await message.reply(f"❌ Xatolik: {str(e)}")
            import logging
            logging.error(f"Error in boost command: {e}", exc_info=True)
        finally:
            await session.close()
    
    async def handle_fixchannel_command(self, message: Message) -> None:
        """Handle /fixchannel command - fix channel ID"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        # Parse command: /fixchannel <new_channel_id> or /fixchannel @username
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri formatlar:\n"
                "1. <code>/fixchannel -1001234567890</code>\n"
                "2. <code>/fixchannel @channel_username</code>\n\n"
                "Bu buyruq birinchi kanalni yangi ID bilan yangilaydi."
            )
            return
        
        channel_input = parts[1]
        
        # Check if it's a username or ID
        if channel_input.startswith('@'):
            # Username format
            try:
                chat = await self.bot.get_chat(channel_input)
                new_channel_id = chat.id
                channel_title = chat.title
            except Exception as e:
                await message.reply(f"❌ Kanal topilmadi: {channel_input}\n\nXatolik: {e}")
                return
        else:
            # Numeric ID format
            try:
                new_channel_id = int(channel_input)
                # Try to get channel info
                try:
                    chat = await self.bot.get_chat(new_channel_id)
                    channel_title = chat.title
                except Exception:
                    channel_title = "Unknown"
            except ValueError:
                await message.reply("❌ Kanal ID raqam bo'lishi kerak yoki @ bilan boshlanishi kerak!")
                return
        
        session = await self.database.get_session()
        try:
            from sqlalchemy import select
            result = await session.execute(select(Channel).where(Channel.is_active == True))
            channels = result.scalars().all()
            
            if not channels:
                await message.reply("❌ Hech qanday kanal topilmadi!")
                return
            
            # Update first channel
            channel = channels[0]
            old_id = channel.channel_id
            channel.channel_id = new_channel_id
            channel.channel_title = channel_title
            await session.commit()
            
            await message.reply(
                f"✅ Kanal ID yangilandi!\n\n"
                f"Kanal: {channel_title}\n"
                f"Eski ID: <code>{old_id}</code>\n"
                f"Yangi ID: <code>{new_channel_id}</code>\n\n"
                f"Endi /boost buyrug'ini ishlating:\n"
                f"<code>/boost https://t.me/{channel_input.replace('@', '')}/&lt;post_id&gt;</code>"
            )
            
        except Exception as e:
            await message.reply(f"❌ Xatolik: {str(e)}")
            import logging
            logging.error(f"Error in fixchannel command: {e}", exc_info=True)
        finally:
            await session.close()
    
    async def handle_boostmulti_command(self, message: Message) -> None:
        """Handle /boostmulti command - boost a post multiple times"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        # Parse command: /boostmulti <post_link> <count>
        parts = message.text.split()
        
        if len(parts) < 2 or len(parts) > 3:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri formatlar:\n"
                "1. <code>/boostmulti https://t.me/channel/123</code> (so'raydi nechta)\n"
                "2. <code>/boostmulti https://t.me/channel/123 5</code> (5 marta)\n\n"
                "Bu buyruq bir postga bir necha marta reaksiya qo'shadi."
            )
            return
        
        post_link = parts[1]
        
        # Get count if provided, otherwise ask
        if len(parts) == 3:
            try:
                count = int(parts[2])
                if count < 1 or count > 10:
                    await message.reply("❌ Soni 1 dan 10 gacha bo'lishi kerak!")
                    return
            except ValueError:
                await message.reply("❌ Soni raqam bo'lishi kerak!")
                return
        else:
            # Ask for count using inline keyboard
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Store post link in a simpler format for callback
            # Use a simple counter instead of parsing the link
            if not hasattr(self, '_custom_boost_counter'):
                self._custom_boost_counter = 0
            
            self._custom_boost_counter += 1
            callback_id = self._custom_boost_counter
            callback_prefix = f"cb_{callback_id}"
            
            keyboard_buttons = []
            row = []
            for count in [1, 2, 3, 4, 5, 10]:
                row.append(InlineKeyboardButton(text=f"{count} marta", callback_data=f"{callback_prefix}_count_{count}"))
                if len(row) == 3:
                    keyboard_buttons.append(row)
                    row = []
            if row:
                keyboard_buttons.append(row)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await message.reply(
                f"🔢 Necha marta reaksiya qo'shilsin?\n\n"
                f"Post: {post_link}",
                reply_markup=keyboard
            )
            return
        
        # Parse link and boost
        await self._boost_post_multiple_times(message, post_link, count)
    
    async def _boost_post_multiple_times(self, message: Message, post_link: str, count: int) -> None:
        """Boost a post multiple times"""
        # Parse link
        if 't.me/' not in post_link:
            await message.reply("❌ Noto'g'ri link format!")
            return
        
        try:
            link_parts = post_link.split('/')
            
            if '/c/' in post_link:
                # Private channel
                channel_id_str = link_parts[-2]
                post_id = int(link_parts[-1])
                channel_id = int(f"-100{channel_id_str}")
            else:
                # Public channel
                username = link_parts[-2]
                post_id = int(link_parts[-1])
                
                try:
                    chat = await self.bot.get_chat(f"@{username}")
                    channel_id = chat.id
                except Exception as e:
                    await message.reply(f"❌ Kanal topilmadi: @{username}\n\nXatolik: {e}")
                    return
        except Exception as e:
            await message.reply(f"❌ Link noto'g'ri formatda!\n\nXatolik: {e}")
            return
        
        # Get channel from database
        session = await self.database.get_session()
        try:
            from sqlalchemy import select
            result = await session.execute(
                select(Channel).where(
                    Channel.channel_id == channel_id,
                    Channel.is_active == True
                )
            )
            channel = result.scalar_one_or_none()
            
            if not channel:
                await message.reply(
                    f"❌ Kanal topilmadi!\n\n"
                    f"Kanal ID: <code>{channel_id}</code>\n\n"
                    f"Avval /fixchannel buyrug'i bilan kanalni qo'shing."
                )
                return
            
            if not channel.reaction_settings:
                await message.reply(
                    f"❌ Kanal uchun reaksiya sozlamalari yo'q!\n\n"
                    f"Avval reaksiya sozlamalarini o'rnating."
                )
                return
            
            # Initialize service
            from ..services.reaction_boost_service import ReactionBoostService
            from ..models.reaction_settings import ReactionSettings
            
            settings = ReactionSettings.from_dict(channel.reaction_settings)
            reaction_service = ReactionBoostService(self.bot, session)
            
            # Create fake message
            class FakeMessage:
                def __init__(self, chat_id, message_id):
                    self.chat = type('obj', (object,), {'id': chat_id})()
                    self.message_id = message_id
            
            fake_msg = FakeMessage(channel_id, post_id)
            
            await message.reply(
                f"⏳ Reaksiyalar qo'shilmoqda...\n\n"
                f"Kanal: {channel.channel_title}\n"
                f"Post ID: {post_id}\n"
                f"Marta: {count}\n"
                f"Emojilar: {' '.join(settings.emojis[:settings.reaction_count])}"
            )
            
            # Boost multiple times
            total_reactions = 0
            for i in range(count):
                try:
                    await reaction_service.boost_post(channel, fake_msg, force=True)
                    total_reactions += settings.reaction_count
                    
                    # Small delay between boosts
                    if i < count - 1:
                        await asyncio.sleep(1)
                except Exception as e:
                    await message.reply(f"❌ {i+1}-marta xatolik: {str(e)}")
                    break
            
            await message.reply(
                f"✅ Reaksiyalar qo'shildi!\n\n"
                f"Kanal: {channel.channel_title}\n"
                f"Post ID: {post_id}\n"
                f"Jami: {total_reactions} ta reaksiya"
            )
            
        except Exception as e:
            await message.reply(f"❌ Xatolik: {str(e)}")
            import logging
            logging.error(f"Error in boostmulti command: {e}", exc_info=True)
        finally:
            await session.close()
    
    async def handle_customboost_command(self, message: Message) -> None:
        """Handle /customboost command - custom emoji and count selection"""
        user_id = message.from_user.id
        
        if user_id not in self.config.ADMIN_USER_IDS:
            await message.reply("❌ Sizda admin huquqlari yo'q.")
            return
        
        # Parse command: /customboost <post_link>
        parts = message.text.split()
        
        if len(parts) != 2:
            await message.reply(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format:\n"
                "<code>/customboost https://t.me/channel/123</code>\n\n"
                "Bu buyruq sizga emoji va sonni tanlash imkonini beradi."
            )
            return
        
        post_link = parts[1]
        
        # Parse link to validate
        if 't.me/' not in post_link:
            await message.reply("❌ Noto'g'ri link format!")
            return
        
        # Initialize session storage
        if not hasattr(self, '_custom_boost_selections'):
            self._custom_boost_selections = {}
        if not hasattr(self, '_custom_boost_counter'):
            self._custom_boost_counter = 0
        
        # Generate unique session ID
        self._custom_boost_counter += 1
        session_id = self._custom_boost_counter
        
        # Show emoji selection keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # All valid Telegram reaction emojis (complete list)
        emojis = [
            '👍', '👎', '❤️', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱',
            '🤬', '😢', '🎉', '🤩', '🤮', '💩', '🙏', '👌', '🕊', '🤡',
            '🥱', '🥴', '😍', '🐳', '🌚', '🌭', '💯', '🤣', '🍌', '🏆',
            '💔', '🤨', '😐', '🍓', '😈', '😴', '😭', '🤓', '👻', '👀',
            '🎃', '🙈', '😇', '😨', '🤗', '🎅', '🎄', '💅', '🤪', '🗿',
            '💘', '🙉', '😘', '💊', '🙊', '😎', '👾', '😡', '🥳', '🤫'
        ]
        
        keyboard_buttons = []
        row = []
        for idx, emoji in enumerate(emojis):
            row.append(InlineKeyboardButton(text=emoji, callback_data=f"cbs_{session_id}_e_{idx}"))
            if len(row) == 4:
                keyboard_buttons.append(row)
                row = []
        if row:
            keyboard_buttons.append(row)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="✅ Tayyor (tanlangan emojilar bilan)", callback_data=f"cbs_{session_id}_done")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.reply(
            f"😊 <b>Emojilarni tanlang</b>\n\n"
            f"Post: {post_link}\n\n"
            f"Qaysi emojilarni qo'shmoqchisiz? (bir nechta tanlash mumkin)",
            reply_markup=keyboard
        )
        
        # Store selection in memory with session ID
        self._custom_boost_selections[session_id] = {
            'user_id': user_id,
            'post_link': post_link,
            'emojis': [],
            'emoji_list': emojis  # Store emoji list for reference
        }
    
    async def _handle_custom_boost_callback(self, callback: CallbackQuery) -> None:
        """Handle custom boost emoji/count selection callbacks"""
        user_id = callback.from_user.id
        data = callback.data
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Custom boost callback: user={user_id}, data={data}")
        
        if not hasattr(self, '_custom_boost_selections'):
            self._custom_boost_selections = {}
        
        # Parse callback data: cbs_<session_id>_<action>_<value>
        # Examples: cbs_1_e_0, cbs_1_done, cbs_1_count_3, cbs_1_back
        parts = data.split("_")
        logger.info(f"Parsed parts: {parts}, len={len(parts)}")
        
        if len(parts) < 3 or parts[0] != "cbs":
            logger.warning(f"Invalid callback format: {data}")
            await callback.answer("❌ Noto'g'ri buyruq")
            return
        
        session_id = int(parts[1])
        
        # Find session
        if session_id not in self._custom_boost_selections:
            await callback.answer("❌ Sessiya tugagan. Qaytadan /customboost buyrug'ini ishlating.")
            return
        
        selection = self._custom_boost_selections[session_id]
        
        # Verify user owns this session
        if selection['user_id'] != user_id:
            await callback.answer("❌ Bu sizning sessiyangiz emas.")
            return
        
        action = parts[2]
        
        # Handle different actions
        if action == "done":
            logger.info("Done button clicked")
            # Done selecting emojis, now ask for count
            if not selection['emojis']:
                await callback.answer("❌ Kamida bitta emoji tanlang!")
                return
            
            # Show count selection
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="1 ta", callback_data=f"cbs_{session_id}_count_1"),
                    InlineKeyboardButton(text="2 ta", callback_data=f"cbs_{session_id}_count_2"),
                    InlineKeyboardButton(text="3 ta", callback_data=f"cbs_{session_id}_count_3"),
                ],
                [
                    InlineKeyboardButton(text="4 ta", callback_data=f"cbs_{session_id}_count_4"),
                    InlineKeyboardButton(text="5 ta", callback_data=f"cbs_{session_id}_count_5"),
                    InlineKeyboardButton(text="10 ta", callback_data=f"cbs_{session_id}_count_10"),
                ],
                [
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"cbs_{session_id}_back")
                ]
            ])
            
            selected_text = ' '.join(selection['emojis'])
            
            await callback.message.edit_text(
                f"🔢 <b>Nechta reaksiya qo'shilsin?</b>\n\n"
                f"Post: {selection['post_link']}\n"
                f"Emojilar: {selected_text}\n\n"
                f"Har bir emojidan nechta qo'shilsin?",
                reply_markup=keyboard
            )
            
            await callback.answer()
        
        elif action == "count":
            logger.info("Count button clicked")
            # Count selected: cbs_1_count_3
            if len(parts) < 4:
                await callback.answer("❌ Noto'g'ri format")
                return
            
            count = int(parts[3])
            logger.info(f"Count: {count}")
            
            # Now boost the post
            await self._custom_boost_post(callback.message, selection, count)
            
            # Clear selection
            del self._custom_boost_selections[session_id]
            
            await callback.answer()
        
        elif action == "back":
            logger.info("Back button clicked")
            # Go back to emoji selection - rebuild the emoji keyboard
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            emoji_list = selection['emoji_list']
            
            keyboard_buttons = []
            row = []
            for idx, e in enumerate(emoji_list):
                # Add checkmark if selected
                text = f"✅ {e}" if e in selection['emojis'] else e
                row.append(InlineKeyboardButton(text=text, callback_data=f"cbs_{session_id}_e_{idx}"))
                if len(row) == 4:
                    keyboard_buttons.append(row)
                    row = []
            if row:
                keyboard_buttons.append(row)
            
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Tayyor (tanlangan emojilar bilan)", callback_data=f"cbs_{session_id}_done")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            selected_text = ' '.join(selection['emojis']) if selection['emojis'] else 'Hech narsa tanlanmagan'
            
            await callback.message.edit_text(
                f"😊 <b>Emojilarni tanlang</b>\n\n"
                f"Post: {selection['post_link']}\n\n"
                f"<b>Tanlangan:</b> {selected_text}\n\n"
                f"Qaysi emojilarni qo'shmoqchisiz? (bir nechta tanlash mumkin)",
                reply_markup=keyboard
            )
            
            await callback.answer()
        
        elif action == "e":
            logger.info("Emoji button clicked")
            # Emoji selection: cbs_1_e_0 (index)
            if len(parts) < 4:
                await callback.answer("❌ Noto'g'ri format")
                return
            
            emoji_idx = int(parts[3])
            emoji = selection['emoji_list'][emoji_idx]
            logger.info(f"Emoji: {emoji}, index: {emoji_idx}")
            
            if emoji in selection['emojis']:
                selection['emojis'].remove(emoji)
                await callback.answer(f"❌ {emoji} olib tashlandi")
            else:
                selection['emojis'].append(emoji)
                await callback.answer(f"✅ {emoji} qo'shildi")
            
            # Update message to show selected emojis
            selected_text = ' '.join(selection['emojis']) if selection['emojis'] else 'Hech narsa tanlanmagan'
            
            # Rebuild keyboard with updated selection
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            emoji_list = selection['emoji_list']
            
            keyboard_buttons = []
            row = []
            for idx, e in enumerate(emoji_list):
                # Add checkmark if selected
                text = f"✅ {e}" if e in selection['emojis'] else e
                row.append(InlineKeyboardButton(text=text, callback_data=f"cbs_{session_id}_e_{idx}"))
                if len(row) == 4:
                    keyboard_buttons.append(row)
                    row = []
            if row:
                keyboard_buttons.append(row)
            
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Tayyor (tanlangan emojilar bilan)", callback_data=f"cbs_{session_id}_done")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(
                f"😊 <b>Emojilarni tanlang</b>\n\n"
                f"Post: {selection['post_link']}\n\n"
                f"<b>Tanlangan:</b> {selected_text}\n\n"
                f"Qaysi emojilarni qo'shmoqchisiz? (bir nechta tanlash mumkin)",
                reply_markup=keyboard
            )
        
        else:
            logger.warning(f"Unknown action: {action}")
            await callback.answer("❌ Noto'g'ri buyruq")
    
    async def _custom_boost_post(self, message: Message, selection: dict, count_per_emoji: int) -> None:
        """Boost a post with custom emoji selection - single bot, single reaction"""
        post_link = selection['post_link']
        emojis = selection['emojis']
        
        # Parse link
        try:
            link_parts = post_link.split('/')
            
            if '/c/' in post_link:
                channel_id_str = link_parts[-2]
                post_id = int(link_parts[-1])
                channel_id = int(f"-100{channel_id_str}")
            else:
                username = link_parts[-2]
                post_id = int(link_parts[-1])
                
                try:
                    chat = await self.bot.get_chat(f"@{username}")
                    channel_id = chat.id
                except Exception as e:
                    await message.reply(f"❌ Kanal topilmadi: @{username}\n\nXatolik: {e}")
                    return
        except Exception as e:
            await message.reply(f"❌ Link noto'g'ri formatda!\n\nXatolik: {e}")
            return
        
        # Get channel from database
        session = await self.database.get_session()
        try:
            from sqlalchemy import select
            result = await session.execute(
                select(Channel).where(
                    Channel.channel_id == channel_id,
                    Channel.is_active == True
                )
            )
            channel = result.scalar_one_or_none()
            
            if not channel:
                await message.reply(
                    f"❌ Kanal topilmadi!\n\n"
                    f"Kanal ID: <code>{channel_id}</code>\n\n"
                    f"Avval /fixchannel buyrug'i bilan kanalni qo'shing."
                )
                return
            
            await message.reply(
                f"⏳ Reaksiya qo'shilmoqda...\n\n"
                f"Kanal: {channel.channel_title}\n"
                f"Post ID: {post_id}\n"
                f"Tanlangan emojilar: {' '.join(emojis)}\n\n"
                f"💡 Eslatma: Bir bot bir postga faqat bitta reaksiya qo'sha oladi.\n"
                f"Oxirgi tanlangan emoji qo'shiladi."
            )
            
            # Add reactions - only last one will remain
            from ..services.reaction_boost_service import ReactionBoostService
            import random
            
            reaction_service = ReactionBoostService(self.bot, session)
            failed_emojis = []
            last_successful_emoji = None
            
            # Try each emoji - Telegram will replace the previous reaction
            for emoji in emojis:
                try:
                    await reaction_service._add_reaction_with_retry(
                        str(channel_id),
                        post_id,
                        emoji
                    )
                    last_successful_emoji = emoji
                    
                    # Small delay before next emoji
                    if emoji != emojis[-1]:
                        await asyncio.sleep(random.uniform(0.5, 1))
                        
                except Exception as e:
                    error_msg = str(e)
                    if "REACTION_INVALID" in error_msg:
                        if emoji not in failed_emojis:
                            failed_emojis.append(emoji)
                    else:
                        import logging
                        logging.error(f"Failed to add reaction {emoji}: {e}")
                        failed_emojis.append(emoji)
            
            # Send result
            result_text = ""
            if last_successful_emoji:
                result_text = f"✅ Reaksiya qo'shildi: {last_successful_emoji}\n\n"
                result_text += f"Kanal: {channel.channel_title}\n"
                result_text += f"Post ID: {post_id}\n\n"
                result_text += f"💡 Bir bot bir postga faqat bitta reaksiya qo'sha oladi.\n"
                result_text += f"Oxirgi tanlangan emoji qo'shildi."
            else:
                result_text = f"❌ Hech qanday reaksiya qo'shilmadi"
            
            if failed_emojis:
                result_text += f"\n\n⚠️ Qo'shilmagan emojilar: {' '.join(failed_emojis)}"
            
            await message.reply(result_text)
            
        except Exception as e:
            await message.reply(f"❌ Xatolik: {str(e)}")
            import logging
            logging.error(f"Error in custom boost: {e}", exc_info=True)
        finally:
            await session.close()
    
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
        elif data.startswith("reaction_settings_"):
            channel_id = int(data.split("_")[2])
            await self._show_reaction_settings(callback.message, channel_id, edit=True)
        elif data.startswith("enable_reaction_"):
            channel_id = int(data.split("_")[2])
            await self._enable_reaction_mode(callback.message, channel_id)
        elif data.startswith("set_emojis_"):
            channel_id = int(data.split("_")[2])
            await self._prompt_set_emojis(callback.message, channel_id, edit=True)
        elif data.startswith("set_count_"):
            channel_id = int(data.split("_")[2])
            await self._prompt_set_count(callback.message, channel_id, edit=True)
        elif data.startswith("toggle_auto_"):
            channel_id = int(data.split("_")[2])
            await self._toggle_auto_boost(callback.message, channel_id)
        elif data.startswith("emoji_"):
            parts = data.split("_")
            channel_id = int(parts[1])
            emoji = parts[2]
            await self._add_emoji(callback.message, channel_id, emoji)
        elif data.startswith("count_"):
            parts = data.split("_")
            channel_id = int(parts[1])
            count = int(parts[2])
            await self._set_reaction_count(callback.message, channel_id, count)
        elif data.startswith("bm_"):
            # Format: bm_c_<channel_id>_<post_id>_<count> or bm_u_<username>_<post_id>_<count>
            parts = data.split("_")
            if len(parts) >= 5:
                link_type = parts[1]  # 'c' or 'u'
                if link_type == 'c':
                    # Private channel: bm_c_1234567890_123_5
                    channel_part = parts[2]
                    post_id = parts[3]
                    count = int(parts[4])
                    post_link = f"https://t.me/c/{channel_part}/{post_id}"
                elif link_type == 'u':
                    # Public channel: bm_u_username_123_5
                    username = parts[2]
                    post_id = parts[3]
                    count = int(parts[4])
                    post_link = f"https://t.me/{username}/{post_id}"
                else:
                    return
                
                await self._boost_post_multiple_times(callback.message, post_link, count)
        elif data.startswith("cbs_"):
            # Custom boost callbacks (session-based)
            await self._handle_custom_boost_callback(callback)
            return  # Don't call callback.answer() again since it's handled in the method
        
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
                ai_text = 'Yoqilgan' if channel.ai_enabled else 'Ochirilgan'
                text += f"   AI: {ai_text}\n\n"
                
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
            mode_text = {
                'comment': 'Faqat komentlarga javob',
                'reaction': 'Faqat reaksiya qoshish',
                'both': 'Ikkalasi ham'
            }.get(channel.mode, 'Komentlarga javob')
            
            text = (
                f"📢 <b>{channel.channel_title}</b>\n\n"
                f"🆔 <b>ID:</b> <code>{channel.channel_id}</code>\n"
                f"💬 <b>Discussion Group:</b> <code>{channel.discussion_group_id or 'Yoq'}</code>\n"
                f"🔧 <b>Rejim:</b> {mode_text}\n"
                f"🤖 <b>AI:</b> {ai_status}\n"
                f"🔧 <b>Provider:</b> {channel.ai_provider}\n"
                f"📊 <b>Kunlik limit:</b> {channel.daily_limit}\n"
                f"⏱ <b>Rate limit:</b> {channel.rate_limit_minutes} daqiqa\n"
                f"📝 <b>Trigger so'zlar:</b> {len(channel.trigger_words)} ta\n"
            )
            
            # Add reaction settings if mode includes reaction
            if channel.mode in ['reaction', 'both'] and channel.reaction_settings:
                settings = channel.reaction_settings
                emojis = settings.get('emojis', [])
                text += f"\n❤️ <b>Reaksiya sozlamalari:</b>\n"
                text += f"   • Emojilar: {' '.join(emojis[:5])}\n"
                text += f"   • Soni: {settings.get('reaction_count', 0)} ta\n"
                text += f"   • Kutish: {settings.get('delay_min', 0)}-{settings.get('delay_max', 0)}s\n"
                auto_icon = 'ON' if settings.get('auto_boost') else 'OFF'
                text += f"   • Auto: {auto_icon}\n"
            
            keyboard_buttons = [
                [InlineKeyboardButton(
                    text="AI Ochirish" if channel.ai_enabled else "AI Yoqish",
                    callback_data=f"toggle_ai_{channel.id}"
                )]
            ]
            
            # Add reaction settings button
            if channel.mode in ['reaction', 'both']:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="❤️ Reaksiya sozlamalari",
                        callback_data=f"reaction_settings_{channel.id}"
                    )
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="❤️ Reaksiya rejimini yoqish",
                        callback_data=f"enable_reaction_{channel.id}"
                    )
                ])
            
            keyboard_buttons.append([
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="show_channels")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
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

    
    async def _show_reaction_settings(self, message: Message, channel_id: int, edit: bool = False) -> None:
        """Show reaction settings for a channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one_or_none()
            
            if not channel:
                await message.reply("❌ Kanal topilmadi.")
                return
            
            settings = channel.reaction_settings or {}
            emojis = settings.get('emojis', [])
            count = settings.get('reaction_count', 3)
            delay_min = settings.get('delay_min', 2.0)
            delay_max = settings.get('delay_max', 8.0)
            auto_boost = settings.get('auto_boost', True)
            
            auto_status = "Yoqilgan" if auto_boost else "O'chirilgan"
            
            text = (
                f"❤️ <b>Reaksiya sozlamalari</b>\n"
                f"📢 <b>Kanal:</b> {channel.channel_title}\n\n"
                f"😊 <b>Emojilar:</b> {' '.join(emojis) if emojis else 'Tanlanmagan'}\n"
                f"🔢 <b>Har postga:</b> {count} ta reaksiya\n"
                f"⏱ <b>Kutish vaqti:</b> {delay_min}-{delay_max} soniya\n"
                f"🤖 <b>Auto-boost:</b> {auto_status}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="😊 Emojilarni o'zgartirish", callback_data=f"set_emojis_{channel_id}")],
                [InlineKeyboardButton(text="🔢 Sonini o'zgartirish", callback_data=f"set_count_{channel_id}")],
                [InlineKeyboardButton(
                    text="Auto-boost O'chirish" if auto_boost else "Auto-boost Yoqish",
                    callback_data=f"toggle_auto_{channel_id}"
                )],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"channel_{channel_id}")]
            ])
            
            if edit and message:
                await message.edit_text(text, reply_markup=keyboard)
            else:
                await message.reply(text, reply_markup=keyboard)
        finally:
            await session.close()
    
    async def _enable_reaction_mode(self, message: Message, channel_id: int) -> None:
        """Enable reaction mode for a channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one_or_none()
            
            if not channel:
                return
            
            # Set default reaction settings
            channel.mode = 'both' if channel.mode == 'comment' else 'reaction'
            channel.reaction_settings = {
                'emojis': ['👍', '❤️', '🔥', '😍', '🎉'],
                'reaction_count': 3,
                'delay_min': 2.0,
                'delay_max': 8.0,
                'auto_boost': True
            }
            
            await session.commit()
            await self._show_channel_details(message, channel_id, edit=True)
        finally:
            await session.close()
    
    async def _prompt_set_emojis(self, message: Message, channel_id: int, edit: bool = False) -> None:
        """Prompt user to set emojis"""
        text = (
            "😊 <b>Emojilarni tanlang</b>\n\n"
            "Quyidagi emojilardan tanlang (tugmani bosing):\n"
        )
        
        # Popular emojis - only valid Telegram reaction emojis
        emojis = [
            '👍', '👎', '❤️', '🔥', '🥰', '👏', '😁', '🤔', '🤯', '😱',
            '🤬', '😢', '🎉', '🤩', '🤮', '💩', '🙏', '👌', '🕊', '🤡',
            '🥱', '🥴', '😍', '🐳', '🌚', '🌭', '💯', '🤣', '🍌', '🏆',
            '💔', '🤨', '😐', '🍓', '😈', '😴', '😭', '🤓', '👻', '👀',
            '🎃', '🙈', '😇', '😨', '🤗', '🎅', '🎄', '💅', '🤪', '🗿',
            '💘', '🙉', '😘', '💊', '🙊', '😎', '👾', '😡', '🥳', '🤫'
        ]
        
        keyboard_buttons = []
        row = []
        for i, emoji in enumerate(emojis):
            row.append(InlineKeyboardButton(text=emoji, callback_data=f"emoji_{channel_id}_{emoji}"))
            if len(row) == 4:
                keyboard_buttons.append(row)
                row = []
        if row:
            keyboard_buttons.append(row)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="✅ Tayyor", callback_data=f"reaction_settings_{channel_id}")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"reaction_settings_{channel_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        if edit and message:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply(text, reply_markup=keyboard)
    
    async def _prompt_set_count(self, message: Message, channel_id: int, edit: bool = False) -> None:
        """Prompt user to set reaction count"""
        text = (
            "🔢 <b>Reaksiya sonini tanlang</b>\n\n"
            "Har bir postga nechta reaksiya qo'shilsin?"
        )
        
        keyboard_buttons = []
        for count in [1, 2, 3, 4, 5]:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"{count} ta", callback_data=f"count_{channel_id}_{count}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"reaction_settings_{channel_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        if edit and message:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.reply(text, reply_markup=keyboard)
    
    async def _toggle_auto_boost(self, message: Message, channel_id: int) -> None:
        """Toggle auto-boost for a channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one_or_none()
            
            if not channel or not channel.reaction_settings:
                return
            
            settings = channel.reaction_settings
            settings['auto_boost'] = not settings.get('auto_boost', True)
            channel.reaction_settings = settings
            
            await session.commit()
            await self._show_reaction_settings(message, channel_id, edit=True)
        finally:
            await session.close()

    
    async def _add_emoji(self, message: Message, channel_id: int, emoji: str) -> None:
        """Add or remove emoji from reaction settings"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one_or_none()
            
            if not channel:
                return
            
            settings = channel.reaction_settings or {
                'emojis': [],
                'reaction_count': 3,
                'delay_min': 2.0,
                'delay_max': 8.0,
                'auto_boost': True
            }
            
            emojis = settings.get('emojis', [])
            
            if emoji in emojis:
                emojis.remove(emoji)
            else:
                emojis.append(emoji)
            
            settings['emojis'] = emojis
            channel.reaction_settings = settings
            
            await session.commit()
            
            # Refresh the emoji selection screen
            try:
                await self._prompt_set_emojis(message, channel_id, edit=True)
            except Exception:
                # If edit fails, send new message
                await self._prompt_set_emojis(message, channel_id, edit=False)
        finally:
            await session.close()
    
    async def _set_reaction_count(self, message: Message, channel_id: int, count: int) -> None:
        """Set reaction count for a channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one_or_none()
            
            if not channel or not channel.reaction_settings:
                return
            
            settings = channel.reaction_settings
            settings['reaction_count'] = count
            channel.reaction_settings = settings
            
            await session.commit()
            await self._show_reaction_settings(message, channel_id, edit=True)
        finally:
            await session.close()
