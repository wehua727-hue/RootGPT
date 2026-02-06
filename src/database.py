"""
Database connection and session management
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: str):
        """Initialize database connection"""
        self.database_url = database_url
        
        # Convert sqlite URL for async usage
        if database_url.startswith("sqlite:///"):
            self.database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif database_url.startswith("sqlite://"):
            self.database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
        
        # Create async engine
        engine_kwargs = {}
        if "sqlite" in self.database_url:
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                },
            })
        
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            **engine_kwargs
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def initialize(self) -> None:
        """Initialize database tables"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connection"""
        await self.engine.dispose()
        logger.info("Database connection closed")
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.async_session()
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            async with self.async_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False