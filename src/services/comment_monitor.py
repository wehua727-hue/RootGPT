"""
Comment monitoring service for processing discussion group messages
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select, func
from datetime import datetime, timedelta

from ..config import Config
from ..database import Database
from ..models import Channel, Comment, CommentCategory, Blacklist, BlacklistType
from ..services.response_generator import ResponseGenerator
from ..services.technical_question_detector import TechnicalQuestionDetector
from ..services.technical_ai_service import TechnicalAIService

logger = logging.getLogger(__name__)


class CommentMonitor:
    """Service for monitoring and processing comments"""
    
    def __init__(self, bot: Bot, database: Database, config: Config):
        self.bot = bot
        self.database = database
        self.config = config
        self.response_generator = ResponseGenerator(bot, database, config)
        
        # Initialize technical components
        self.technical_detector = TechnicalQuestionDetector()
        self.technical_ai_service = TechnicalAIService(config)
        logger.info("CommentMonitor initialized with technical Q&A support")
    
    async def process_comment(self, message: Message, channel: Channel) -> None:
        """Process a comment from discussion group"""
        try:
            # Validate comment
            if not await self.is_valid_comment(message):
                return
            
            # Check spam protection
            if not await self.check_spam_protection(message.from_user.id, channel.id):
                logger.info(f"Comment blocked by spam protection: user {message.from_user.id}")
                return
            
            # NEW: Check if technical question
            is_technical = await self.technical_detector.is_technical_question(message.text)
            
            if is_technical:
                logger.info(f"Technical question detected from user {message.from_user.id}")
                await self._process_technical_comment(message, channel)
            else:
                # Existing flow for non-technical comments
                await self._process_standard_comment(message, channel)
            
        except Exception as e:
            logger.error(f"Error processing comment: {e}")
    
    async def _process_technical_comment(self, message: Message, channel: Channel) -> None:
        """Process technical question"""
        try:
            # Extract technical context
            tech_context = await self.technical_detector.extract_technical_context(message.text)
            code_snippet = await self.technical_detector.detect_code_snippet(message.text)
            error_info = await self.technical_detector.detect_error_message(message.text)
            
            logger.info(f"Technical context: lang={tech_context.primary_language}, "
                       f"framework={tech_context.framework}, confidence={tech_context.confidence:.2f}")
            
            # Generate technical response
            response_text = await self.technical_ai_service.generate_technical_response(
                user_question=message.text,
                technical_context=tech_context,
                code_snippet=code_snippet,
                error_info=error_info
            )
            
            # Send response
            await message.reply(response_text, parse_mode="Markdown")
            
            logger.info(f"Technical response sent to user {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Error processing technical comment: {e}")
            # Fallback to standard processing
            await self._process_standard_comment(message, channel)
    
    async def _process_standard_comment(self, message: Message, channel: Channel) -> None:
        """Process standard (non-technical) comment"""
        try:
            # Create comment record
            comment = await self._create_comment_record(message, channel)
            
            # Analyze and categorize comment
            from ..services.comment_analyzer import CommentAnalyzer
            analyzer = CommentAnalyzer(self.database, self.config)
            
            category = await analyzer.categorize_comment(message.text)
            comment.category = category
            
            # Check if we should respond
            should_respond = await analyzer.should_respond(comment, channel)
            comment.should_respond = should_respond
            comment.processed = True
            
            # Save comment
            session = await self.database.get_session()
            try:
                session.add(comment)
                await session.commit()
                await session.refresh(comment)
            finally:
                await session.close()
            
            # Generate and send response if needed
            if should_respond:
                await self.response_generator.generate_and_send_response(comment, channel)
            
            logger.info(f"Processed comment {comment.id} from user {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Error processing standard comment: {e}")
    
    async def is_valid_comment(self, message: Message) -> bool:
        """Check if message is a valid comment to process"""
        # Must have text
        if not message.text or not message.text.strip():
            return False
        
        # Must have user
        if not message.from_user:
            return False
        
        # Skip bot messages
        if message.from_user.is_bot:
            return False
        
        # Skip commands
        if message.text.startswith('/'):
            return False
        
        # Allow emoji and short messages (changed from 3 to 1)
        if len(message.text.strip()) < 1:
            return False
        
        return True
    
    async def check_spam_protection(self, user_id: int, channel_id: int) -> bool:
        """Check spam protection rules"""
        # VAQTINCHA O'CHIRILGAN - test uchun
        return True
        
        session = await self.database.get_session()
        try:
            # Check blacklist
            blacklist_check = await session.execute(
                select(Blacklist).where(
                    Blacklist.entry_type == BlacklistType.USER,
                    Blacklist.user_id == user_id,
                    Blacklist.is_active == True,
                    (Blacklist.channel_id == channel_id) | (Blacklist.channel_id.is_(None))
                )
            )
            
            if blacklist_check.scalar_one_or_none():
                return False
            
            # Check rate limiting
            rate_limit_minutes = await self._get_rate_limit(channel_id)
            cutoff_time = datetime.now() - timedelta(minutes=rate_limit_minutes)
            
            recent_responses = await session.execute(
                select(func.count()).select_from(
                    select(Comment.id)
                    .join(Comment.responses)
                    .where(
                        Comment.user_id == user_id,
                        Comment.channel_id == channel_id,
                        Comment.created_at >= cutoff_time
                    )
                    .subquery()
                )
            )
            
            if recent_responses.scalar() > 0:
                return False
            
            # Check daily limit
            daily_limit = await self._get_daily_limit(channel_id)
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_responses = await session.execute(
                select(func.count()).select_from(
                    select(Comment.id)
                    .join(Comment.responses)
                    .where(
                        Comment.channel_id == channel_id,
                        Comment.created_at >= today_start
                    )
                    .subquery()
                )
            )
            
            if today_responses.scalar() >= daily_limit:
                return False
            
            return True
        finally:
            await session.close()
    
    async def _create_comment_record(self, message: Message, channel: Channel) -> Comment:
        """Create comment record in database"""
        return Comment(
            message_id=message.message_id,
            user_id=message.from_user.id,
            username=message.from_user.username,
            text=message.text,
            channel_id=channel.id,
            category=CommentCategory.GENERAL,  # Will be updated by analyzer
            processed=False,
            should_respond=False
        )
    
    async def _get_rate_limit(self, channel_id: int) -> int:
        """Get rate limit for channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(
                select(Channel.rate_limit_minutes).where(Channel.id == channel_id)
            )
            rate_limit = result.scalar_one_or_none()
            return rate_limit or self.config.RATE_LIMIT_MINUTES
        finally:
            await session.close()
    
    async def _get_daily_limit(self, channel_id: int) -> int:
        """Get daily limit for channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(
                select(Channel.daily_limit).where(Channel.id == channel_id)
            )
            daily_limit = result.scalar_one_or_none()
            return daily_limit or self.config.DAILY_RESPONSE_LIMIT
        finally:
            await session.close()