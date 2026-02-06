"""
Tests for ReactionBoostService
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from src.models import Base, Channel, BoostedPost, ActivityLog
from src.models.reaction_settings import ReactionSettings
from src.services.reaction_boost_service import ReactionBoostService
from telegram.error import RetryAfter, Forbidden


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session"""
    # Create in-memory SQLite database for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def test_channel(db_session):
    """Create a test channel with reaction settings"""
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction",
        reaction_settings={
            "emojis": ["👍", "❤️", "🔥", "😍"],
            "reaction_count": 3,
            "delay_min": 0.1,
            "delay_max": 0.2,
            "auto_boost": True
        }
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
def mock_bot():
    """Create a mock Telegram Bot"""
    bot = MagicMock()
    bot.set_message_reaction = AsyncMock()
    return bot


@pytest_asyncio.fixture
async def reaction_service(mock_bot, db_session):
    """Create a ReactionBoostService instance"""
    return ReactionBoostService(mock_bot, db_session)


@pytest.mark.asyncio
async def test_is_already_boosted_returns_false_for_new_post(db_session, test_channel, reaction_service):
    """Test that _is_already_boosted returns False for a new post"""
    result = await reaction_service._is_already_boosted(test_channel.id, 999)
    assert result is False


@pytest.mark.asyncio
async def test_is_already_boosted_returns_true_for_existing_post(db_session, test_channel, reaction_service):
    """Test that _is_already_boosted returns True for an already boosted post"""
    # Create a boosted post record
    boosted_post = BoostedPost(
        channel_id=test_channel.id,
        post_id=999,
        boost_timestamp=datetime.now(timezone.utc),
        reaction_count=3,
        emojis_used=["👍", "❤️", "🔥"]
    )
    db_session.add(boosted_post)
    await db_session.commit()
    
    # Check if already boosted
    result = await reaction_service._is_already_boosted(test_channel.id, 999)
    assert result is True


@pytest.mark.asyncio
async def test_select_random_emojis_returns_correct_count(reaction_service):
    """Test that _select_random_emojis returns the correct number of emojis"""
    settings = ReactionSettings(
        emojis=["👍", "❤️", "🔥", "😍", "🎉"],
        reaction_count=3,
        delay_min=1.0,
        delay_max=2.0,
        auto_boost=True
    )
    
    result = reaction_service._select_random_emojis(settings)
    
    assert len(result) == 3
    assert all(emoji in settings.emojis for emoji in result)


@pytest.mark.asyncio
async def test_select_random_emojis_shuffles_order(reaction_service):
    """Test that _select_random_emojis produces different orderings"""
    settings = ReactionSettings(
        emojis=["👍", "❤️", "🔥", "😍", "🎉"],
        reaction_count=5,
        delay_min=1.0,
        delay_max=2.0,
        auto_boost=True
    )
    
    # Get multiple selections
    results = [reaction_service._select_random_emojis(settings) for _ in range(10)]
    
    # Check that not all results are identical (very unlikely with shuffling)
    unique_results = [tuple(r) for r in results]
    assert len(set(unique_results)) > 1, "Emoji selection should produce different orderings"


@pytest.mark.asyncio
async def test_mark_as_boosted_creates_record(db_session, test_channel, reaction_service):
    """Test that _mark_as_boosted creates a BoostedPost record"""
    emojis = ["👍", "❤️", "🔥"]
    
    await reaction_service._mark_as_boosted(
        test_channel.id,
        999,
        len(emojis),
        emojis
    )
    
    # Query the database
    result = await db_session.execute(
        select(BoostedPost).where(
            BoostedPost.channel_id == test_channel.id,
            BoostedPost.post_id == 999
        )
    )
    boosted_post = result.scalar_one_or_none()
    
    assert boosted_post is not None
    assert boosted_post.channel_id == test_channel.id
    assert boosted_post.post_id == 999
    assert boosted_post.reaction_count == 3
    assert boosted_post.emojis_used == emojis
    assert boosted_post.boost_timestamp is not None


@pytest.mark.asyncio
async def test_add_reaction_with_retry_success(mock_bot, reaction_service):
    """Test that _add_reaction_with_retry successfully adds a reaction"""
    await reaction_service._add_reaction_with_retry("123456789", 999, "👍")
    
    # Verify the bot method was called
    mock_bot.set_message_reaction.assert_called_once()
    call_args = mock_bot.set_message_reaction.call_args
    assert call_args.kwargs["chat_id"] == "123456789"
    assert call_args.kwargs["message_id"] == 999


@pytest.mark.asyncio
async def test_add_reaction_with_retry_handles_retry_after(mock_bot, reaction_service):
    """Test that _add_reaction_with_retry handles RetryAfter errors"""
    # Mock the bot to raise RetryAfter on first call, then succeed
    mock_bot.set_message_reaction.side_effect = [
        RetryAfter(1),
        None
    ]
    
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        await reaction_service._add_reaction_with_retry("123456789", 999, "👍")
        
        # Verify sleep was called with retry_after value
        mock_sleep.assert_called_once_with(1)
        
        # Verify the bot method was called twice
        assert mock_bot.set_message_reaction.call_count == 2


@pytest.mark.asyncio
async def test_add_reaction_with_retry_raises_after_max_retries(mock_bot, reaction_service):
    """Test that _add_reaction_with_retry raises after max retries"""
    # Mock the bot to always raise RetryAfter
    mock_bot.set_message_reaction.side_effect = RetryAfter(1)
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        with pytest.raises(RetryAfter):
            await reaction_service._add_reaction_with_retry("123456789", 999, "👍")
        
        # Verify the bot method was called max_retries times
        assert mock_bot.set_message_reaction.call_count == 3


@pytest.mark.asyncio
async def test_handle_api_error_logs_permission_error(db_session, test_channel, mock_bot, reaction_service):
    """Test that _handle_api_error logs permission errors"""
    mock_post = MagicMock()
    mock_post.message_id = 999
    
    error = Forbidden("Bot is not admin")
    
    await reaction_service._handle_api_error(test_channel, mock_post, "👍", error)
    
    # Query the activity log
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.activity_type == "error"
        )
    )
    log = result.scalar_one_or_none()
    
    assert log is not None
    assert log.details["error_type"] == "permission_error"


@pytest.mark.asyncio
async def test_handle_api_error_disables_reaction_mode(db_session, test_channel, mock_bot, reaction_service):
    """Test that _handle_api_error disables reaction mode on permission error"""
    mock_post = MagicMock()
    mock_post.message_id = 999
    
    error = Forbidden("Bot is not admin")
    
    # Channel starts with 'reaction' mode
    assert test_channel.mode == "reaction"
    
    await reaction_service._handle_api_error(test_channel, mock_post, "👍", error)
    
    # Refresh the channel from database
    await db_session.refresh(test_channel)
    
    # Mode should be changed to 'comment'
    assert test_channel.mode == "comment"


@pytest.mark.asyncio
async def test_boost_post_skips_already_boosted(db_session, test_channel, mock_bot, reaction_service):
    """Test that boost_post skips posts that are already boosted"""
    # Create a boosted post record
    boosted_post = BoostedPost(
        channel_id=test_channel.id,
        post_id=999,
        boost_timestamp=datetime.now(timezone.utc),
        reaction_count=3,
        emojis_used=["👍", "❤️", "🔥"]
    )
    db_session.add(boosted_post)
    await db_session.commit()
    
    # Create mock post
    mock_post = MagicMock()
    mock_post.message_id = 999
    
    # Try to boost
    await reaction_service.boost_post(test_channel, mock_post)
    
    # Verify no reactions were added
    mock_bot.set_message_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_boost_post_skips_when_auto_boost_disabled(db_session, mock_bot, reaction_service):
    """Test that boost_post skips when auto_boost is disabled"""
    # Create channel with auto_boost disabled
    channel = Channel(
        channel_id=987654321,
        channel_title="Test Channel",
        mode="reaction",
        reaction_settings={
            "emojis": ["👍", "❤️"],
            "reaction_count": 2,
            "delay_min": 0.1,
            "delay_max": 0.2,
            "auto_boost": False
        }
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create mock post
    mock_post = MagicMock()
    mock_post.message_id = 999
    
    # Try to boost
    await reaction_service.boost_post(channel, mock_post)
    
    # Verify no reactions were added
    mock_bot.set_message_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_boost_post_adds_reactions_and_logs(db_session, test_channel, mock_bot, reaction_service):
    """Test that boost_post successfully adds reactions and logs activities"""
    # Create mock post
    mock_post = MagicMock()
    mock_post.message_id = 999
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await reaction_service.boost_post(test_channel, mock_post)
    
    # Verify reactions were added (should be 3 based on reaction_count)
    assert mock_bot.set_message_reaction.call_count == 3
    
    # Verify BoostedPost was created
    result = await db_session.execute(
        select(BoostedPost).where(
            BoostedPost.channel_id == test_channel.id,
            BoostedPost.post_id == 999
        )
    )
    boosted_post = result.scalar_one_or_none()
    assert boosted_post is not None
    assert boosted_post.reaction_count == 3
    
    # Verify activity logs were created (3 reactions + 1 completion)
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.post_id == 999
        )
    )
    logs = result.scalars().all()
    assert len(logs) == 4  # 3 reaction_added + 1 boost_completed
    
    reaction_logs = [log for log in logs if log.activity_type == "reaction_added"]
    completion_logs = [log for log in logs if log.activity_type == "boost_completed"]
    
    assert len(reaction_logs) == 3
    assert len(completion_logs) == 1
    assert completion_logs[0].details["reaction_count"] == 3
