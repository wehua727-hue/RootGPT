"""
Test script to manually add reactions to channel posts
"""

import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()

async def test_add_reaction():
    """Test adding reaction to a channel post"""
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    
    # Get channel ID and message ID from user
    channel_id = input("Kanal ID kiriting (masalan: -1001234567890): ")
    message_id = int(input("Post ID kiriting: "))
    emoji = input("Emoji kiriting (masalan: 👍): ")
    
    try:
        # Try to add reaction
        await bot.set_message_reaction(
            chat_id=channel_id,
            message_id=message_id,
            reaction=[{"type": "emoji", "emoji": emoji}],
            is_big=False
        )
        print(f"✅ Reaksiya qo'shildi: {emoji}")
    except Exception as e:
        print(f"❌ Xatolik: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_add_reaction())
