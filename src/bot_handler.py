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
from .services.reaction_boost_service import ReactionBoostService
from .services.post_monitor_service import PostMonitorService

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
        
        # Initialize reaction boost services
        self.reaction_boost_service: Optional[ReactionBoostService] = None
        self.post_monitor_service: Optional[PostMonitorService] = None
        
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
        
        self.dp.message.register(
            self.admin_handler.handle_boost_command,
            lambda message: message.text and message.text.startswith('/boost')
        )
        
        self.dp.message.register(
            self.admin_handler.handle_fixchannel_command,
            lambda message: message.text and message.text.startswith('/fixchannel')
        )
        
        self.dp.message.register(
            self.admin_handler.handle_boostmulti_command,
            lambda message: message.text and message.text.startswith('/boostmulti')
        )
        
        self.dp.message.register(
            self.admin_handler.handle_customboost_command,
            lambda message: message.text and message.text.startswith('/customboost')
        )
        
        # Callback queries for admin interface
        self.dp.callback_query.register(
            self.admin_handler.handle_callback_query
        )
        
        # Channel post handler (for reaction boosting)
        self.dp.channel_post.register(
            self._handle_channel_post
        )
        
        # Regular messages (comments from discussion groups)
        self.dp.message.register(
            self.message_handler.handle_message
        )
        
        # Error handler
        self.dp.errors.register(self._error_handler)
    
    async def _error_handler(self, event, data: dict) -> None:
        """Handle errors during message processing"""
        exception = data.get('exception')
        update = data.get('update')
        
        if exception:
            logger.error(f"Error processing update: {exception}", exc_info=True)
        
        # Try to send error message to admin if possible
        if update and update.message and update.message.from_user:
            user_id = update.message.from_user.id
            if user_id in self.config.ADMIN_USER_IDS:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Xatolik yuz berdi: {str(exception)[:200]}..."
                    )
                except Exception as e:
                    logger.error(f"Failed to send error message to admin: {e}")
    
    async def _initialize_services(self) -> None:
        """Initialize reaction boost services"""
        try:
            # Get database session
            session = await self.database.get_session()
            
            # Initialize ReactionBoostService
            self.reaction_boost_service = ReactionBoostService(self.bot, session)
            logger.info("ReactionBoostService initialized")
            
            # Initialize PostMonitorService
            self.post_monitor_service = PostMonitorService(
                self.bot, 
                session, 
                self.reaction_boost_service
            )
            logger.info("PostMonitorService initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            # Don't raise - bot can still work without reaction boosting
    
    async def _handle_channel_post(self, message: Message) -> None:
        """Handle new posts in channels (for reaction boosting)"""
        try:
            logger.info(f"Received channel post: chat_id={message.chat.id}, message_id={message.message_id}")
            
            if not self.post_monitor_service:
                logger.warning("PostMonitorService not initialized")
                return
            
            # Get channel from database
            from sqlalchemy import select
            from .models import Channel
            
            session = await self.database.get_session()
            try:
                result = await session.execute(
                    select(Channel).where(
                        Channel.channel_id == message.chat.id,
                        Channel.is_active == True
                    )
                )
                channel = result.scalar_one_or_none()
                
                if not channel:
                    logger.warning(f"Channel {message.chat.id} not found in database")
                    return
                
                logger.info(f"Found channel: {channel.channel_title}, mode={channel.mode}, reaction_settings={channel.reaction_settings}")
                
                if channel and (channel.mode == 'reaction' or channel.mode == 'both'):
                    logger.info(f"Processing channel post {message.message_id} in channel {channel.channel_id}")
                    await self.post_monitor_service.process_channel_post(channel, message)
                else:
                    logger.info(f"Channel mode is '{channel.mode}', skipping reaction boost")
                
            finally:
                await session.close()
                
        except Exception as e:
            logger.error(f"Error handling channel post: {e}", exc_info=True)
    
    async def start_bot(self) -> None:
        """Start the bot"""
        try:
            # Validate bot token
            bot_info = await self.bot.get_me()
            logger.info(f"Bot started: @{bot_info.username} ({bot_info.first_name})")
            
            # Initialize reaction boost services
            await self._initialize_services()
            
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
            BotCommand(command="boost", description="Postga reaksiya qo'shish"),
            BotCommand(command="boostmulti", description="Postga ko'p marta reaksiya"),
            BotCommand(command="customboost", description="Emoji va sonni tanlash"),
            BotCommand(command="fixchannel", description="Kanal ID ni tuzatish"),
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