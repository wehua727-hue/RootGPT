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
        
        # Initialize and start bot
        bot_handler = BotHandler(config, database)
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