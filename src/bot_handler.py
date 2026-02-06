"""
Main bot handler for Telegram integration
"""

import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .config import Config
from .database import Database
from .handlers.admin_handler import AdminHandler
from .handlers.message_handler import MessageHandler

logger = logging.getLogger(__name__)


class BotHandler:
    """Main bot handler class"""
    
    def __init__(self, config: Config, database: Database):
        """Initialize bot handler"""
        self.config = config
        self.database = database
        
        # Initialize bot with default properties
        default_properties = DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True
        )
        
        self.bot = Bot(
            token=config.BOT_TOKEN,
            default=default_properties
        )
        
        # Initialize dispatcher
        self.dp = Dispatcher()
        
        # Initialize handlers
        self.admin_handler = AdminHandler(self.bot, self.database, self.config)
        self.message_handler = MessageHandler(self.bot, self.database, self.config)
        
        # Register handlers
        self._register_handlers()
        
        # Web app for webhook (if needed)
        self.app: Optional[web.Application] = None
        self.webhook_handler: Optional[SimpleRequestHandler] = None
    
    def _register_handlers(self) -> None:
        """Register message handlers with dispatcher"""
        # Admin commands
        self.dp.message.register(
            self.admin_handler.handle_start_command,
            lambda message: message.text and message.text.startswith('/start')
        )
        
        self.dp.message.register(
            self.admin_handler.handle_stats_command,
            lambda message: message.text and message.text.startswith('/stats')
        )
        
        self.dp.message.register(
            self.admin_handler.handle_settings_command,
            lambda message: message.text and message.text.startswith('/settings')
        )
        
        # Callback queries for admin interface
        self.dp.callback_query.register(
            self.admin_handler.handle_callback_query
        )
        
        # Regular messages (comments from discussion groups)
        self.dp.message.register(
            self.message_handler.handle_message
        )
        
        # Error handler
        self.dp.error.register(self._error_handler)
    
    async def _error_handler(self, update: Update, exception: Exception) -> None:
        """Handle errors during message processing"""
        logger.error(f"Error processing update {update.update_id}: {exception}")
        
        # Try to send error message to admin if possible
        if update.message and update.message.from_user:
            user_id = update.message.from_user.id
            if user_id in self.config.ADMIN_USER_IDS:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Xatolik yuz berdi: {str(exception)[:200]}..."
                    )
                except Exception as e:
                    logger.error(f"Failed to send error message to admin: {e}")
    
    async def start_bot(self) -> None:
        """Start the bot"""
        try:
            # Validate bot token
            bot_info = await self.bot.get_me()
            logger.info(f"Bot started: @{bot_info.username} ({bot_info.first_name})")
            
            # Set bot commands
            await self._set_bot_commands()
            
            if self.config.WEBHOOK_URL:
                # Start with webhook
                await self._start_webhook()
            else:
                # Start with polling
                await self._start_polling()
                
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
    
    async def stop_bot(self) -> None:
        """Stop the bot"""
        try:
            if self.config.WEBHOOK_URL:
                # Delete webhook
                await self.bot.delete_webhook()
                logger.info("Webhook deleted")
            
            # Close bot session
            await self.bot.session.close()
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    async def _set_bot_commands(self) -> None:
        """Set bot commands for better UX"""
        from aiogram.types import BotCommand
        
        commands = [
            BotCommand(command="start", description="Bot boshqaruv paneli"),
            BotCommand(command="stats", description="Statistika ko'rish"),
            BotCommand(command="settings", description="Sozlamalar"),
        ]
        
        await self.bot.set_my_commands(commands)
        logger.info("Bot commands set successfully")
    
    async def _start_polling(self) -> None:
        """Start bot with polling"""
        logger.info("Starting bot with polling...")
        await self.dp.start_polling(self.bot)
    
    async def _start_webhook(self) -> None:
        """Start bot with webhook"""
        logger.info(f"Starting bot with webhook: {self.config.WEBHOOK_URL}")
        
        # Create webhook handler
        self.webhook_handler = SimpleRequestHandler(
            dispatcher=self.dp,
            bot=self.bot
        )
        
        # Create web application
        self.app = web.Application()
        self.webhook_handler.register(self.app, path="/webhook")
        
        # Set webhook
        await self.bot.set_webhook(
            url=f"{self.config.WEBHOOK_URL}/webhook",
            drop_pending_updates=True
        )
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host="0.0.0.0", port=8080)
        await site.start()
        
        logger.info("Webhook server started on port 8080")
    
    async def validate_token(self) -> bool:
        """Validate bot token"""
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Token valid for bot: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"Invalid bot token: {e}")
            return False