"""
Fix channel ID in database
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import select, update
from src.database import Database
from src.models import Channel

load_dotenv()

async def fix_channel_id():
    """Fix the channel ID in database"""
    db = Database()
    await db.initialize()
    
    session = await db.get_session()
    try:
        # Get all channels
        result = await session.execute(select(Channel))
        channels = result.scalars().all()
        
        print(f"Found {len(channels)} channels:")
        for channel in channels:
            print(f"  - ID: {channel.id}, Channel ID: {channel.channel_id}, Title: {channel.channel_title}")
        
        # Update the channel with ID 0 or wrong ID
        if channels:
            channel = channels[0]  # Get first channel
            
            # Ask user for correct channel ID
            correct_id = input(f"\nEnter correct channel ID for '{channel.channel_title}': ")
            correct_id = int(correct_id)
            
            # Update channel
            channel.channel_id = correct_id
            await session.commit()
            
            print(f"\n✅ Channel ID updated: {correct_id}")
            print(f"Now you can use: /boost {correct_id} <post_id>")
        else:
            print("No channels found!")
    
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(fix_channel_id())
