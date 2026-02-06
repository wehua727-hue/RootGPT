#!/usr/bin/env python3
"""
Automatic channel setup for Railway deployment
"""

import asyncio
import os
from sqlalchemy import select
from src.database import Database
from src.models import Channel
from src.config import Config


async def setup_channel():
    """Setup channel automatically from environment variables"""
    
    # Get config
    config = Config()
    
    # Initialize database
    database = Database(config.DATABASE_URL)
    await database.initialize()
    
    # Channel info from environment
    discussion_group_id = -1003022082883  # Your discussion group ID
    channel_title = "RootGPT Channel"
    
    print(f"Setting up channel: {channel_title}")
    print(f"Discussion Group ID: {discussion_group_id}")
    
    # Create channel
    session = await database.get_session()
    try:
        # Check if channel already exists
        result = await session.execute(
            select(Channel).where(Channel.discussion_group_id == discussion_group_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"✅ Channel already exists: {existing.channel_title}")
        else:
            # Create new channel
            channel = Channel(
                channel_id=0,  # Will be updated later
                channel_title=channel_title,
                discussion_group_id=discussion_group_id,
                ai_enabled=True,
                ai_provider="groq",
                trigger_words=[],
                rate_limit_minutes=1,
                daily_limit=1000
            )
            
            session.add(channel)
            await session.commit()
            await session.refresh(channel)
            
            print(f"✅ Channel created successfully! ID: {channel.id}")
            print(f"   Title: {channel.channel_title}")
            print(f"   Discussion Group: {channel.discussion_group_id}")
            print(f"   AI Enabled: {channel.ai_enabled}")
    
    finally:
        await session.close()
        await database.close()
    
    print("\n🎉 Setup complete! Bot is ready to respond to comments.")


if __name__ == "__main__":
    asyncio.run(setup_channel())
