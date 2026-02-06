#!/usr/bin/env python3
"""
Telegram AI Bot - Main Entry Point
Intelligent automated response system for Telegram business channels
"""

import asyncio
import logging
import sys
from pathlib import Path

from src.bot_handler import BotHandler
from src.config import Config
from src.database import Database


async def setup_default_channel(database: Database):
    """Setup default channel if not exists"""
    try:
        from src.models import Channel
        from sqlalchemy import select
        
        discussion_group_id = -1003022082883  # Your discussion group ID
        
        session = await database.get_session()
        try:
            # Check if channel exists
            result = await session.execute(
                select(Channel).where(Channel.discussion_group_id == discussion_group_id)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Create default channel
                channel = Channel(
                    channel_id=0,
                    channel_title="RootGPT Channel",
                    discussion_group_id=discussion_group_id,
                    ai_enabled=True,
                    ai_provider="groq",
                    trigger_words=[],
                    rate_limit_minutes=1,
                    daily_limit=1000
                )
                
                session.add(channel)
                await session.commit()
                logging.info(f"✅ Default channel created: {channel.channel_title}")
            else:
                logging.info(f"✅ Channel already exists: {existing.channel_title}")
        
        finally:
            await session.close()
    
    except Exception as e:
        logging.error(f"Failed to setup default channel: {e}")


async def main():
    """Main application entry point"""
    try:
        # Initialize configuration
        config = Config()
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Starting Telegram AI Bot...")
        
        # Initialize database
        database = Database(config.DATABASE_URL)
        await database.initialize()
        
        # Setup default channel (for Railway deployment)
        await setup_default_channel(database)
        
        # Initialize bot handler
        bot_handler = BotHandler(config, database)
        
        # Delete webhook if exists (important for Railway/cloud deployment)
        try:
            await bot_handler.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted successfully")
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")
        
        # Start bot
        await bot_handler.start_bot()
        
        logger.info("Bot started successfully!")
        
        # Keep the bot running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal...")
        finally:
            await bot_handler.stop_bot()
            await database.close()
            logger.info("Bot stopped successfully!")
            
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())