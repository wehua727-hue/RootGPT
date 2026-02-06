"""
Comment analysis service for categorizing and processing comments
"""

import logging
import re
from typing import List, Set
from sqlalchemy import select

from ..config import Config
from ..database import Database
from ..models import Channel, Comment, CommentCategory

logger = logging.getLogger(__name__)


class CommentAnalyzer:
    """Service for analyzing and categorizing comments"""
    
    def __init__(self, database: Database, config: Config):
        self.database = database
        self.config = config
        
        # Define keyword patterns for each category
        self.category_keywords = {
            CommentCategory.PRICE: {
                'uzbek': ['narx', 'necha', 'qancha', 'pul', 'som', 'dollar', 'rub', 'chegirma', 'arzon', 'qimmat'],
                'russian': ['цена', 'сколько', 'стоит', 'рубль', 'доллар', 'сум', 'скидка', 'дешево', 'дорого'],
                'english': ['price', 'cost', 'how much', 'dollar', 'sum', 'discount', 'cheap', 'expensive']
            },
            CommentCategory.LOCATION: {
                'uzbek': ['manzil', 'qayerda', 'joylashuv', 'shahar', 'tuman', 'ko\'cha', 'yetkazib berish', 'dostavka'],
                'russian': ['адрес', 'где', 'местоположение', 'город', 'район', 'улица', 'доставка'],
                'english': ['address', 'where', 'location', 'city', 'delivery', 'shipping']
            },
            CommentCategory.CONTACT: {
                'uzbek': ['telefon', 'raqam', 'bog\'lanish', 'aloqa', 'telegram', 'whatsapp', 'instagram'],
                'russian': ['телефон', 'номер', 'связь', 'контакт', 'телеграм', 'ватсап', 'инстаграм'],
                'english': ['phone', 'number', 'contact', 'telegram', 'whatsapp', 'instagram', 'call']
            },
            CommentCategory.ORDER: {
                'uzbek': ['buyurtma', 'sotib olish', 'xarid', 'kerak', 'olaman', 'beraman', 'zakaz'],
                'russian': ['заказ', 'купить', 'покупка', 'нужно', 'возьму', 'дам', 'хочу'],
                'english': ['order', 'buy', 'purchase', 'need', 'want', 'take', 'get']
            }
        }
        
        # Common trigger words that should always get a response
        self.default_triggers = [
            'narx', 'necha', 'qancha', 'manzil', 'qayerda', 'telefon', 'buyurtma',
            'цена', 'сколько', 'адрес', 'где', 'телефон', 'заказ',
            'price', 'how much', 'address', 'where', 'phone', 'order'
        ]
    
    async def categorize_comment(self, text: str) -> CommentCategory:
        """Categorize comment based on content analysis"""
        if not text:
            return CommentCategory.GENERAL
        
        text_lower = text.lower()
        category_scores = {category: 0 for category in CommentCategory}
        
        # Score each category based on keyword matches
        for category, languages in self.category_keywords.items():
            for language, keywords in languages.items():
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        category_scores[category] += 1
        
        # Find category with highest score
        max_score = max(category_scores.values())
        if max_score == 0:
            return CommentCategory.GENERAL
        
        # Return category with highest score
        for category, score in category_scores.items():
            if score == max_score:
                return category
        
        return CommentCategory.GENERAL
    
    async def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from comment text"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_keywords = []
        
        # Extract keywords from all categories
        for category, languages in self.category_keywords.items():
            for language, keywords in languages.items():
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        found_keywords.append(keyword)
        
        return list(set(found_keywords))  # Remove duplicates
    
    async def should_respond(self, comment: Comment, channel: Channel) -> bool:
        """Determine if bot should respond to this comment"""
        try:
            # Check if AI is enabled for this channel
            if not channel.ai_enabled:
                return False
            
            # Bot har qanday komentga javob beradi (suhbatlashish uchun)
            # Faqat juda qisqa xabarlarni ignore qiladi
            if len(comment.text.strip()) < 2:
                return False
            
            # Bot commands ni ignore qiladi
            if comment.text.startswith('/'):
                return False
            
            # Har qanday boshqa komentga javob beradi
            return True
            
        except Exception as e:
            logger.error(f"Error determining response necessity: {e}")
            return False
    
    async def _is_question(self, text: str) -> bool:
        """Check if text contains question patterns"""
        question_patterns = [
            # Uzbek question patterns
            r'\b(nima|qanday|qachon|qayerda|qancha|necha|kim|nega|qanaqasiga)\b',
            r'\?',  # Question mark
            
            # Russian question patterns  
            r'\b(что|как|когда|где|сколько|кто|почему|какой)\b',
            
            # English question patterns
            r'\b(what|how|when|where|how much|who|why|which)\b'
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    async def get_response_priority(self, comment: Comment) -> int:
        """Get response priority based on comment category and content"""
        priority_map = {
            CommentCategory.ORDER: 5,      # Highest priority - potential sale
            CommentCategory.PRICE: 4,      # High priority - price inquiry
            CommentCategory.CONTACT: 3,    # Medium-high priority
            CommentCategory.LOCATION: 2,   # Medium priority
            CommentCategory.GENERAL: 1     # Lowest priority
        }
        
        base_priority = priority_map.get(comment.category, 1)
        
        # Boost priority for questions
        if await self._is_question(comment.text.lower()):
            base_priority += 1
        
        # Boost priority for urgent keywords
        urgent_keywords = ['tez', 'shoshilinch', 'срочно', 'urgent', 'быстро', 'fast']
        text_lower = comment.text.lower()
        
        for keyword in urgent_keywords:
            if keyword in text_lower:
                base_priority += 2
                break
        
        return min(base_priority, 10)  # Cap at 10
    
    async def analyze_sentiment(self, text: str) -> str:
        """Basic sentiment analysis of comment"""
        if not text:
            return 'neutral'
        
        text_lower = text.lower()
        
        # Positive indicators
        positive_words = [
            'yaxshi', 'ajoyib', 'zo\'r', 'mukammal', 'rahmat',
            'хорошо', 'отлично', 'супер', 'спасибо', 'класс',
            'good', 'great', 'excellent', 'thanks', 'awesome'
        ]
        
        # Negative indicators
        negative_words = [
            'yomon', 'noto\'g\'ri', 'xato', 'muammo', 'shikoyat',
            'плохо', 'неправильно', 'ошибка', 'проблема', 'жалоба',
            'bad', 'wrong', 'error', 'problem', 'complaint'
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    async def get_suggested_response_type(self, comment: Comment, channel: Channel) -> str:
        """Suggest whether to use template or AI response"""
        # Use template for common categories if available
        if comment.category in [CommentCategory.PRICE, CommentCategory.CONTACT, CommentCategory.LOCATION]:
            return 'template_preferred'
        
        # Use AI for complex questions or general inquiries
        if comment.category == CommentCategory.GENERAL or await self._is_question(comment.text.lower()):
            return 'ai_preferred'
        
        return 'either'