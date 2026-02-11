"""
AI service for generating responses using multiple providers
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from enum import Enum

# AI Provider imports
try:
    import openai
except ImportError:
    openai = None

try:
    import groq
except ImportError:
    groq = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from ..config import Config

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI provider enumeration"""
    OPENAI = "openai"
    GROQ = "groq"
    GEMINI = "gemini"


class AIService:
    """Service for AI response generation with multiple provider support"""
    
    def __init__(self, config: Config):
        self.config = config
        self.providers = {}
        self.current_provider = AIProvider(config.DEFAULT_AI_PROVIDER)
        
        # Initialize available providers
        self._initialize_providers()
        
        # Uzbek language prompt template - ROOTGPT UNIVERSAL
        self.base_prompt = """Sen RootGPT - universal va juda aqlli AI yordamchisan. Har qanday mavzuda professional gaplasha olasan.

MUHIM: HAR DOIM O'ZBEK TILIDA JAVOB BER! (ALWAYS respond in Uzbek language!)

ASOSIY XUSUSIYATLAR:
1. Har qanday mavzuda chuqur bilimga egasan: fan, texnologiya, san'at, sport, siyosat, iqtisod, madaniyat, tarix, va boshqalar
2. Har bir savolga IXCHAM, ANIQ va FOYDALI javob berasan
3. Murakkab mavzularni oddiy va tushunarli tushuntirasan
4. Mantiqiy va professional fikr yuritasan
5. Yomon so'zlarga - hikmatli va odobli nasihat berasan
6. Video/kanal maqtasa: "Ajoyib! Reaksiya bosishni unutmang! 👍"
7. Salom berma, faqat kerakli javob ber
8. Agar ismingni so'rashsa - "Men RootGPT, universal AI yordamchiman" deb javob ber
9. Har doim samimiy, do'stona va professional bo'l
10. JAVOBNI QISQA VA ANIQ QILIB BER - ortiqcha so'z ishlatma!
11. ODDIY MATN FORMATIDA YOZ - murakkab jadval, markdown yoki maxsus belgilardan foydalanma!

JAVOB FORMATI:
- Oddiy matn ishlatgin (plain text)
- Ro'yxat uchun: 1., 2., 3. yoki • belgisini ishlatgin
- Jadval o'rniga: oddiy ro'yxat yoki paragraflar yozgin
- Emoji ishlatish mumkin: ✅ ❌ 💡 📌 🔥

Xabar: {user_comment}

RootGPT javob (O'zbek tilida, ixcham, oddiy matn):"""
    
    def _initialize_providers(self) -> None:
        """Initialize available AI providers"""
        # Initialize OpenAI
        if openai and self.config.OPENAI_API_KEY:
            try:
                self.providers[AIProvider.OPENAI] = openai.AsyncOpenAI(
                    api_key=self.config.OPENAI_API_KEY
                )
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
        
        # Initialize Groq
        if groq and self.config.GROQ_API_KEY:
            try:
                self.providers[AIProvider.GROQ] = groq.AsyncGroq(
                    api_key=self.config.GROQ_API_KEY
                )
                logger.info("Groq provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")
        
        # Initialize Gemini
        if genai and self.config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=self.config.GEMINI_API_KEY)
                self.providers[AIProvider.GEMINI] = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        
        if not self.providers:
            logger.warning("No AI providers initialized!")
    
    async def generate_response(self, user_comment: str, channel_context: str = "") -> Optional[str]:
        """Generate AI response with fallback to other providers"""
        if not self.providers:
            logger.error("No AI providers available")
            return None
        
        # Try current provider first
        response = await self._try_provider(self.current_provider, user_comment, channel_context)
        if response:
            # Remove unwanted greetings
            response = self._remove_unwanted_greeting(response, user_comment)
            return response
        
        # Try other providers as fallback
        for provider in self.providers:
            if provider != self.current_provider:
                logger.info(f"Trying fallback provider: {provider.value}")
                response = await self._try_provider(provider, user_comment, channel_context)
                if response:
                    # Remove unwanted greetings
                    response = self._remove_unwanted_greeting(response, user_comment)
                    return response
        
        logger.error("All AI providers failed")
        return None
    
    async def _try_provider(self, provider: AIProvider, user_comment: str, channel_context: str) -> Optional[str]:
        """Try to generate response using specific provider"""
        if provider not in self.providers:
            return None
        
        try:
            # Build full prompt with context
            prompt = self.base_prompt.format(user_comment=user_comment)
            
            # Add context if available
            if channel_context:
                prompt = f"{channel_context}\n\n{prompt}"
            
            if provider == AIProvider.OPENAI:
                return await self._generate_openai(prompt)
            elif provider == AIProvider.GROQ:
                return await self._generate_groq(prompt)
            elif provider == AIProvider.GEMINI:
                return await self._generate_gemini(prompt)
            
        except Exception as e:
            logger.error(f"Error with {provider.value} provider: {e}")
            return None
    
    async def _generate_openai(self, prompt: str) -> Optional[str]:
        """Generate response using OpenAI"""
        try:
            client = self.providers[AIProvider.OPENAI]
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Siz professional mijoz xizmati yordamchisisiz."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7,
                timeout=10.0
            )
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content.strip()
                return self._validate_response(content)
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            return None
    
    async def _generate_groq(self, prompt: str) -> Optional[str]:
        """Generate response using Groq"""
        try:
            client = self.providers[AIProvider.GROQ]
            
            response = await client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "Sen RootGPT - universal va juda aqlli AI yordamchisan. HAR DOIM O'ZBEK TILIDA JAVOB BER! Har qanday mavzuda professional gaplasha olasan: fan, texnologiya, san'at, sport, siyosat, iqtisod, madaniyat, tarix va boshqalar. Har bir savolga IXCHAM, ANIQ va FOYDALI javob ber. Ortiqcha so'z ishlatma! Samimiy va professional bo'l."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.8,
                top_p=0.92,
                timeout=40.0
            )
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content.strip()
                return self._validate_response(content)
            
        except Exception as e:
            logger.error(f"Groq generation error: {e}")
            return None
    
    async def _generate_gemini(self, prompt: str) -> Optional[str]:
        """Generate response using Gemini"""
        try:
            model = self.providers[AIProvider.GEMINI]
            
            # Gemini doesn't have async support in the current version
            # So we'll run it in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: model.generate_content(prompt)
            )
            
            if response and response.text:
                content = response.text.strip()
                return self._validate_response(content)
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return None
    
    def _validate_response(self, response: str) -> Optional[str]:
        """Validate and clean AI response"""
        if not response:
            return None
        
        # Remove common AI disclaimers
        response = response.replace("Men AI yordamchiman", "")
        response = response.replace("Men botman", "")
        response = response.replace("I am an AI", "")
        response = response.replace("As an AI", "")
        
        # KUCHLI FILTER: Remove "Mullabek" so'zini har qanday shaklda
        import re
        # Case-insensitive replacement
        response = re.sub(r'\bmullabek\b', '', response, flags=re.IGNORECASE)
        response = re.sub(r'\bmullobek\b', '', response, flags=re.IGNORECASE)
        response = re.sub(r'\bmullatbek\b', '', response, flags=re.IGNORECASE)
        response = re.sub(r'\bmen mullabek\b', '', response, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        response = ' '.join(response.split())
        response = response.strip()
        
        # Check minimum length only
        if len(response) < 3:
            return None
        
        # ALWAYS return the full response - no cutting!
        return response
    
    def _remove_unwanted_greeting(self, response: str, user_message: str) -> str:
        """Remove 'Salom' from response if user didn't greet"""
        user_lower = user_message.lower().strip()
        
        # Check if user greeted
        greetings = ['salom', 'assalomu', 'xayr', 'hello', 'hi']
        user_greeted = any(greeting in user_lower for greeting in greetings)
        
        # Check if user used bad words - don't remove greeting in this case
        bad_words = ['ahmoq', 'jinni', 'telbalo', 'bema\'ni', 'axlat', 'yomon']
        has_bad_words = any(bad_word in user_lower for bad_word in bad_words)
        
        # If user has bad words, keep the response as is (AI will give advice)
        if has_bad_words:
            return response
        
        # If user didn't greet, remove Salom from start of response
        if not user_greeted:
            response_lower = response.lower()
            if response_lower.startswith('salom'):
                # Remove "Salom" and any following punctuation/whitespace
                response = response[5:].lstrip('!.,;: ')
                # Capitalize first letter
                if response:
                    response = response[0].upper() + response[1:]
        
        return response
    
    def _has_uzbek_content(self, text: str) -> bool:
        """Simple check for Uzbek content"""
        # Just check for some basic Uzbek indicators
        uzbek_chars = ['ʻ', 'ʼ', 'oʻ', 'gʻ', 'ʻ']  # Uzbek specific characters
        uzbek_words = ['salom', 'xayr', 'yaxshi', 'rahmat', 'nima', 'qanday', 'bo\'ling', 'sog\'']
        
        text_lower = text.lower()
        
        # Check for Uzbek characters
        for char in uzbek_chars:
            if char in text:
                return True
        
        # Check for common Uzbek words
        for word in uzbek_words:
            if word in text_lower:
                return True
        
        return False
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all AI providers"""
        health_status = {}
        
        for provider in AIProvider:
            if provider in self.providers:
                try:
                    # Try a simple test request
                    test_response = await self._try_provider(
                        provider, 
                        "Salom", 
                        "Test kanal"
                    )
                    health_status[provider.value] = test_response is not None
                except Exception:
                    health_status[provider.value] = False
            else:
                health_status[provider.value] = False
        
        return health_status
    
    async def switch_provider(self, provider: AIProvider) -> bool:
        """Switch to a different AI provider"""
        if provider in self.providers:
            self.current_provider = provider
            logger.info(f"Switched to AI provider: {provider.value}")
            return True
        else:
            logger.error(f"Provider {provider.value} not available")
            return False
    
    def get_available_providers(self) -> list:
        """Get list of available providers"""
        return [provider.value for provider in self.providers.keys()]
    
    def get_current_provider(self) -> str:
        """Get current active provider"""
        return self.current_provider.value