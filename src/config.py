"""
Configuration management for Telegram AI Bot
Handles environment variables and application settings
"""

import os
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """Application configuration manager"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        load_dotenv()
        
        # Telegram Bot Configuration
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
            
        self.WEBHOOK_URL = os.getenv("WEBHOOK_URL")
        
        # AI Service Configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        # Database Configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///telegram_bot.db")
        
        # Bot Configuration
        self.DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "openai")
        self.MAX_RESPONSE_LENGTH = int(os.getenv("MAX_RESPONSE_LENGTH", "200"))
        self.RATE_LIMIT_MINUTES = int(os.getenv("RATE_LIMIT_MINUTES", "5"))
        self.DAILY_RESPONSE_LIMIT = int(os.getenv("DAILY_RESPONSE_LIMIT", "100"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Admin Configuration
        admin_ids = os.getenv("ADMIN_USER_IDS", "")
        self.ADMIN_USER_IDS = [int(uid.strip()) for uid in admin_ids.split(",") if uid.strip()]
    
    def get_ai_api_key(self, provider: str) -> Optional[str]:
        """Get API key for specified AI provider"""
        provider_keys = {
            "openai": self.OPENAI_API_KEY,
            "groq": self.GROQ_API_KEY,
            "gemini": self.GEMINI_API_KEY
        }
        return provider_keys.get(provider.lower())
    
    def validate(self) -> bool:
        """Validate configuration completeness"""
        if not self.BOT_TOKEN:
            return False
            
        # Check if at least one AI provider is configured
        ai_keys = [self.OPENAI_API_KEY, self.GROQ_API_KEY, self.GEMINI_API_KEY]
        if not any(ai_keys):
            return False
            
        return True