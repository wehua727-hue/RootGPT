"""
Response generation service for creating and sending bot responses
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from sqlalchemy import select
from sqlalchemy.sql import func

from ..config import Config
from ..database import Database
from ..models import Channel, Comment, Response, ResponseType, Template, UserGreeting
from .ai_service import AIService

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Service for generating and sending responses"""
    
    def __init__(self, bot: Bot, database: Database, config: Config):
        self.bot = bot
        self.database = database
        self.config = config
        self.ai_service = AIService(config)
        
        # Default fallback responses by category
        self.fallback_responses = {
            'price': "Salom! Narx haqida admin bilan gaplashing.",
            'location': "Salom! Manzil haqida admin ma'lumot beradi.",
            'contact': "Salom! Admin bilan bog'laning.",
            'order': "Salom! Buyurtma uchun adminni chaqiring.",
            'general': "Salom! Qalaysiz?"
        }
    
    async def generate_and_send_response(self, comment: Comment, channel: Channel) -> Optional[Response]:
        """Generate and send response for a comment"""
        try:
            # Generate response text
            response_text, response_type, ai_provider = await self._generate_response_text(comment, channel)
            
            if not response_text:
                logger.warning(f"No response generated for comment {comment.id}")
                return None
            
            # Create response record
            response = Response(
                response_text=response_text,
                response_type=response_type,
                ai_provider=ai_provider,
                comment_id=comment.id,
                channel_id=channel.id,
                sent_successfully=False
            )
            
            # Save response to database
            session = await self.database.get_session()
            try:
                session.add(response)
                await session.commit()
                await session.refresh(response)
            finally:
                await session.close()
            
            # Send response via Telegram
            success = await self._send_response(response, comment, channel)
            
            # Update response status
            session = await self.database.get_session()
            try:
                await session.merge(response)
                response.sent_successfully = success
                await session.commit()
            finally:
                await session.close()
            
            if success:
                logger.info(f"Response {response.id} sent successfully for comment {comment.id}")
            else:
                logger.error(f"Failed to send response {response.id} for comment {comment.id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating/sending response for comment {comment.id}: {e}")
            return None
    
    async def _generate_response_text(self, comment: Comment, channel: Channel) -> tuple[Optional[str], ResponseType, Optional[str]]:
        """Generate response text using templates or AI"""
        # Try template response first
        template_response = await self._get_template_response(comment.category, channel.id)
        if template_response:
            return template_response, ResponseType.TEMPLATE, None
        
        # Try AI response if enabled
        if channel.ai_enabled:
            ai_response = await self._generate_ai_response(comment, channel)
            if ai_response:
                return ai_response, ResponseType.AI_GENERATED, self.ai_service.get_current_provider()
        
        # Fallback to default response
        fallback_response = self._get_fallback_response(comment.category)
        return fallback_response, ResponseType.FALLBACK, None
    
    async def _get_template_response(self, category, channel_id: int) -> Optional[str]:
        """Get template response for category and channel"""
        session = await self.database.get_session()
        try:
            result = await session.execute(
                select(Template).where(
                    Template.channel_id == channel_id,
                    Template.category == category,
                    Template.is_active == True
                ).order_by(Template.priority.desc())
            )
            
            template = result.scalar_one_or_none()
            if template:
                return template.template_text
            
            return None
        finally:
            await session.close()
    
    async def _generate_ai_response(self, comment: Comment, channel: Channel) -> Optional[str]:
        """Generate AI response for comment"""
        try:
            # Check if user has been greeted today
            has_greeted_today = await self._check_daily_greeting(comment.user_id, channel.id)
            
            # Prepare context with recent chat history
            channel_context = f"Kanal: {channel.channel_title}"
            if channel.trigger_words:
                channel_context += f", Asosiy mavzular: {', '.join(channel.trigger_words[:5])}"
            
            # Get recent comments for context (last 3 comments)
            recent_context = await self._get_recent_context(comment.channel_id, comment.id)
            
            # Add greeting instruction to context if not greeted today
            if not has_greeted_today:
                recent_context += f"\n\nBu foydalanuvchiga bugun birinchi marta javob berasiz."
                # Mark as greeted
                await self._mark_user_greeted(comment.user_id, channel.id)
            else:
                recent_context += f"\n\nBu foydalanuvchiga bugun allaqachon javob bergansiz. Salom bermang."
            
            # Generate response with context
            response = await self.ai_service.generate_response(
                user_comment=comment.text,
                channel_context=recent_context
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return None
    
    async def _get_recent_context(self, channel_id: int, current_comment_id: int) -> str:
        """Get recent chat context"""
        try:
            session = await self.database.get_session()
            try:
                # Get last 3 comments before current one
                result = await session.execute(
                    select(Comment).where(
                        Comment.channel_id == channel_id,
                        Comment.id < current_comment_id
                    ).order_by(Comment.id.desc()).limit(3)
                )
                
                recent_comments = list(result.scalars().all())
                
                if not recent_comments:
                    return ""
                
                # Build context string
                context_parts = []
                for comment in reversed(recent_comments):  # Reverse to get chronological order
                    context_parts.append(f"Foydalanuvchi: {comment.text}")
                
                return "Oldingi suhbat: " + " | ".join(context_parts[-2:])  # Last 2 comments
                
            finally:
                await session.close()
        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            return ""
    
    async def _check_daily_greeting(self, user_id: int, channel_id: int) -> bool:
        """Check if user has been greeted today"""
        try:
            from datetime import date
            session = await self.database.get_session()
            try:
                today = date.today()
                result = await session.execute(
                    select(UserGreeting).where(
                        UserGreeting.user_id == user_id,
                        UserGreeting.channel_id == channel_id,
                        UserGreeting.greeting_date == today,
                        UserGreeting.has_greeted == True
                    )
                )
                
                greeting = result.scalar_one_or_none()
                return greeting is not None
                
            finally:
                await session.close()
        except Exception as e:
            logger.error(f"Error checking daily greeting: {e}")
            return False
    
    async def _mark_user_greeted(self, user_id: int, channel_id: int) -> None:
        """Mark user as greeted today"""
        try:
            from datetime import date
            session = await self.database.get_session()
            try:
                today = date.today()
                
                # Check if record exists
                result = await session.execute(
                    select(UserGreeting).where(
                        UserGreeting.user_id == user_id,
                        UserGreeting.channel_id == channel_id,
                        UserGreeting.greeting_date == today
                    )
                )
                
                existing = result.scalar_one_or_none()
                
                if not existing:
                    # Create new greeting record
                    greeting = UserGreeting(
                        user_id=user_id,
                        channel_id=channel_id,
                        greeting_date=today,
                        has_greeted=True
                    )
                    session.add(greeting)
                else:
                    # Update existing record
                    existing.has_greeted = True
                
                await session.commit()
                
            finally:
                await session.close()
        except Exception as e:
            logger.error(f"Error marking user greeted: {e}")
    
    def _get_fallback_response(self, category) -> str:
        """Get fallback response for category"""
        # Samimiy va emoji bilan javoblar
        import random
        
        responses = [
            "😊 Salom! Qalaysiz?",
            "👍 Yaxshi gap! Yana nima kerak?",
            "🤔 Qiziq! Batafsil aytib bering.",
            "😄 Ajoyib! Yordam kerakmi?",
            "🔥 Zo'r! Yana savol bo'lsa so'rang.",
            "😊 Yaxshi! Tinglayapman.",
            "👌 Mayli! Davom eting.",
            "💪 Ajoyib! Ko'proq gaplashaylik."
        ]
        
        return random.choice(responses)
    
    async def _send_response(self, response: Response, comment: Comment, channel: Channel) -> bool:
        """Send response via Telegram"""
        try:
            if not channel.discussion_group_id:
                logger.error(f"No discussion group ID for channel {channel.id}")
                return False
            
            # Send as reply to original comment
            sent_message = await self.bot.send_message(
                chat_id=channel.discussion_group_id,
                text=response.response_text,
                reply_to_message_id=comment.message_id,
                parse_mode=None  # Send as plain text to avoid formatting issues
            )
            
            # Update response with Telegram message ID
            response.telegram_message_id = sent_message.message_id
            
            return True
            
        except TelegramBadRequest as e:
            error_msg = f"Telegram bad request: {e}"
            logger.error(error_msg)
            response.error_message = error_msg
            return False
            
        except TelegramAPIError as e:
            error_msg = f"Telegram API error: {e}"
            logger.error(error_msg)
            response.error_message = error_msg
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error sending message: {e}"
            logger.error(error_msg)
            response.error_message = error_msg
            return False
    
    async def create_template_response(self, channel_id: int, category, name: str, template_text: str) -> Optional[Template]:
        """Create a new template response"""
        try:
            async with self.database.get_session() as session:
                template = Template(
                    name=name,
                    category=category,
                    template_text=template_text,
                    channel_id=channel_id,
                    is_active=True,
                    priority=0
                )
                
                session.add(template)
                await session.commit()
                await session.refresh(template)
                
                logger.info(f"Created template {template.id} for channel {channel_id}")
                return template
                
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return None
    
    async def update_template_response(self, template_id: int, template_text: str) -> bool:
        """Update existing template response"""
        try:
            async with self.database.get_session() as session:
                result = await session.execute(select(Template).where(Template.id == template_id))
                template = result.scalar_one_or_none()
                
                if not template:
                    return False
                
                template.template_text = template_text
                await session.commit()
                
                logger.info(f"Updated template {template_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating template {template_id}: {e}")
            return False
    
    async def delete_template_response(self, template_id: int) -> bool:
        """Delete template response"""
        try:
            async with self.database.get_session() as session:
                result = await session.execute(select(Template).where(Template.id == template_id))
                template = result.scalar_one_or_none()
                
                if not template:
                    return False
                
                template.is_active = False
                await session.commit()
                
                logger.info(f"Deleted template {template_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {e}")
            return False
    
    async def get_channel_templates(self, channel_id: int) -> list:
        """Get all templates for a channel"""
        async with self.database.get_session() as session:
            result = await session.execute(
                select(Template).where(
                    Template.channel_id == channel_id,
                    Template.is_active == True
                ).order_by(Template.category, Template.priority.desc())
            )
            
            return list(result.scalars().all())
    
    async def test_ai_response(self, test_text: str, channel_id: int) -> Optional[str]:
        """Test AI response generation"""
        try:
            async with self.database.get_session() as session:
                result = await session.execute(select(Channel).where(Channel.id == channel_id))
                channel = result.scalar_one_or_none()
                
                if not channel:
                    return None
                
                # Create temporary comment for testing
                test_comment = Comment(
                    message_id=0,
                    user_id=0,
                    text=test_text,
                    channel_id=channel_id
                )
                
                return await self._generate_ai_response(test_comment, channel)
                
        except Exception as e:
            logger.error(f"Error testing AI response: {e}")
            return None