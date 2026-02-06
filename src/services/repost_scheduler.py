"""
Background scheduler for auto-repost monitoring
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.services.auto_repost_service import AutoRepostService

logger = logging.getLogger(__name__)


class RepostScheduler:
    """Background task scheduler for monitoring source channels"""
    
    def __init__(
        self,
        bot: Bot,
        session_maker: async_sessionmaker[AsyncSession],
        interval_seconds: int = 120
    ):
        self.bot = bot
        self.session_maker = session_maker
        self.interval_seconds = interval_seconds
        self.task: Optional[asyncio.Task] = None
        self.running = False
        self.last_execution: Optional[datetime] = None
    
    async def start(self) -> None:
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"RepostScheduler started with interval {self.interval_seconds}s")
    
    async def stop(self) -> None:
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("RepostScheduler stopped")
    
    async def _run(self) -> None:
        """Main scheduler loop"""
        while self.running:
            try:
                logger.info("Starting repost monitoring cycle")
                self.last_execution = datetime.now()
                
                # Create new session for this cycle
                async with self.session_maker() as session:
                    service = AutoRepostService(self.bot, session)
                    await service.monitor_all_sources()
                
                logger.info("Repost monitoring cycle completed")
                
            except asyncio.CancelledError:
                logger.info("Scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler cycle: {e}", exc_info=True)
            
            # Wait for next cycle
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.running
    
    def get_last_execution(self) -> Optional[datetime]:
        """Get last execution time"""
        return self.last_execution
