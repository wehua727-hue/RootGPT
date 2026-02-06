#!/usr/bin/env python3
"""
Manual setup script for adding discussion group
"""

import asyncio
import sys
from src.database import Database
from src.models import Channel

async def manual_setup():
    """Manually add a discussion group"""
    
    # Get discussion group ID from user
    discussion_group_id = input("Discussion group ID ni kiriting (masalan: -1001234567890): ")
    
    try:
        discussion_group_id = int(discussion_group_id)
    except ValueError:
        print("Noto'g'ri ID format!")
        return
    
    # Initialize database
    database = Database("sqlite:///telegram_bot.db")
    await database.initialize()
    
    # Create channel entry
    session = await database.get_session()
    try:
        # Check if already exists
        from sqlalchemy import select
        result = await session.execute(
            select(Channel).where(Channel.discussion_group_id == discussion_group_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Bu group allaqachon ulangan: {existing.channel_title}")
            existing.ai_enabled = True
            existing.admin_user_ids = [5834939103]  # Your user ID
            await session.commit()
            print("AI yoqildi va admin qo'shildi!")
        else:
            # Create new channel with unique channel_id
            import random
            new_channel = Channel(
                channel_id=random.randint(1000000, 9999999),  # Random unique ID
                channel_title=f"Manual Setup Channel",
                discussion_group_id=discussion_group_id,
                ai_enabled=True,
                admin_user_ids=[5834939103]  # Your user ID
            )
            
            session.add(new_channel)
            await session.commit()
            print(f"✅ Discussion group {discussion_group_id} muvaffaqiyatli ulandi!")
            print("Bot endi bu groupdagi har qanday komentga javob beradi!")
            
    finally:
        await session.close()
        await database.close()

if __name__ == "__main__":
    asyncio.run(manual_setup())