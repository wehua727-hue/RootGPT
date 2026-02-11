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
from .handlers.autorepost_handler import AutoRepostHandler
from .handlers.channel_qa_handler import ChannelQAHandler
from .services.reaction_boost_service import ReactionBoostService
from .services.post_monitor_service import PostMonitorService
from .services.repost_scheduler import RepostScheduler

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
        self.autorepost_handler = AutoRepostHandler(self.bot, self.config)
        self.channel_qa_handler = ChannelQAHandler(self.bot, self.database, self.config)
        
        # Initialize reaction boost services
        self.reaction_boost_service: Optional[ReactionBoostService] = None
        self.post_monitor_service: Optional[PostMonitorService] = None
        self.repost_scheduler: Optional[RepostScheduler] = None
        
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
        
        # Auto-repost commands
        self.dp.message.register(
            self._handle_autorepost_command,
            lambda message: message.text and message.text.startswith('/autorepost')
        )
        
        # Channel Q&A commands
        self.dp.message.register(
            self.channel_qa_handler.handle_addchannel_command,
            lambda message: message.text and message.text.startswith('/addchannel')
        )
        
        self.dp.message.register(
            self.channel_qa_handler.handle_listchannels_command,
            lambda message: message.text and message.text.startswith('/listchannels')
        )
        
        self.dp.message.register(
            self.channel_qa_handler.handle_removechannel_command,
            lambda message: message.text and message.text.startswith('/removechannel')
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
            
            # Initialize RepostScheduler
            self.repost_scheduler = RepostScheduler(
                self.bot,
                self.database.session_maker,
                interval_seconds=120  # Check every 2 minutes
            )
            logger.info("RepostScheduler initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            # Don't raise - bot can still work without reaction boosting
    
    async def _handle_channel_post(self, message: Message) -> None:
        """Handle new posts in channels (for reaction boosting and Q&A)"""
        try:
            logger.info(f"Received channel post: chat_id={message.chat.id}, message_id={message.message_id}")
            
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
                
                logger.info(f"Found channel: {channel.channel_title}, mode={channel.mode}")
                
                # Handle reaction boosting
                if self.post_monitor_service and (channel.mode == 'reaction' or channel.mode == 'both'):
                    logger.info(f"Processing channel post {message.message_id} for reaction boost")
                    await self.post_monitor_service.process_channel_post(channel, message)
                
                # NEW: Handle Q&A for ALL channel posts with text
                if message.text:
                    from .services.technical_question_detector import TechnicalQuestionDetector
                    from .services.technical_ai_service import TechnicalAIService
                    from .services.ai_service import AIService
                    
                    logger.info(f"Processing channel post {message.message_id} for Q&A")
                    
                    # Check if technical question
                    detector = TechnicalQuestionDetector()
                    is_technical = await detector.is_technical_question(message.text)
                    
                    response_text = None
                    
                    if is_technical:
                        logger.info(f"Technical question detected in channel post {message.message_id}")
                        
                        # Extract context
                        tech_context = await detector.extract_technical_context(message.text)
                        code_snippet = await detector.detect_code_snippet(message.text)
                        error_info = await detector.detect_error_message(message.text)
                        
                        # Generate technical response
                        tech_ai = TechnicalAIService(self.config)
                        response_text = await tech_ai.generate_technical_response(
                            user_question=message.text,
                            technical_context=tech_context,
                            code_snippet=code_snippet,
                            error_info=error_info
                        )
                    else:
                        logger.info(f"Standard question detected in channel post {message.message_id}")
                        
                        # Generate standard response
                        ai_service = AIService(self.config)
                        response_text = await ai_service.generate_response(message.text)
                    
                    # Send response as comment to the post
                    if response_text:
                        await message.reply(response_text, parse_mode="Markdown")
                        logger.info(f"Response sent to channel post {message.message_id}")
                
            finally:
                await session.close()
                
        except Exception as e:
            logger.error(f"Error handling channel post: {e}", exc_info=True)
    
    async def _handle_autorepost_command(self, message: Message) -> None:
        """Handle /autorepost commands"""
        try:
            session = await self.database.get_session()
            
            # Parse subcommand
            parts = message.text.split()
            if len(parts) < 2:
                await message.reply(
                    "📋 Auto-repost komandalar:\n\n"
                    "/autorepost add <source> <target> - Kanal qo'shish\n"
                    "/autorepost list - Kanallar ro'yxati\n"
                    "/autorepost remove <channel_id> - Kanalni o'chirish\n"
                    "/autorepost enable <channel_id> - Kanalni yoqish\n"
                    "/autorepost disable <channel_id> - Kanalni o'chirish\n"
                    "/autorepost stats [channel_id] - Statistika"
                )
                return
            
            subcommand = parts[1].lower()
            
            if subcommand == 'add':
                await self.autorepost_handler.handle_autorepost_add(message, session)
            elif subcommand == 'list':
                await self.autorepost_handler.handle_autorepost_list(message, session)
            elif subcommand == 'remove':
                await self.autorepost_handler.handle_autorepost_remove(message, session)
            elif subcommand == 'enable':
                await self.autorepost_handler.handle_autorepost_enable(message, session)
            elif subcommand == 'disable':
                await self.autorepost_handler.handle_autorepost_disable(message, session)
            elif subcommand == 'stats':
                await self.autorepost_handler.handle_autorepost_stats(message, session)
            else:
                await message.reply(f"❌ Noma'lum komanda: {subcommand}")
                
        except Exception as e:
            logger.error(f"Error handling autorepost command: {e}", exc_info=True)
            await message.reply(f"❌ Xatolik: {e}")
    
    async def start_bot(self) -> None:
        """Start the bot"""
        try:
            # Validate bot token
            bot_info = await self.bot.get_me()
            logger.info(f"Bot started: @{bot_info.username} ({bot_info.first_name})")
            
            # Initialize reaction boost services
            await self._initialize_services()
            
            # Start repost scheduler
            if self.repost_scheduler:
                await self.repost_scheduler.start()
                logger.info("RepostScheduler started")
            
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
            # Stop repost scheduler
            if self.repost_scheduler:
                await self.repost_scheduler.stop()
                logger.info("RepostScheduler stopped")
            
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
            BotCommand(command="autorepost", description="Avtomatik repost sozlamalari"),
            BotCommand(command="addchannel", description="Kanal qo'shish (Q&A uchun)"),
            BotCommand(command="listchannels", description="Kanallar ro'yxati"),
            BotCommand(command="removechannel", description="Kanalni o'chirish"),
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