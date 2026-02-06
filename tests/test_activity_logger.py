"""
Tests for ActivityLogger service
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from src.models import Base, Channel, ActivityLog
from src.services.activity_logger import ActivityLogger


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
    """Create a test channel"""
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def activity_logger(db_session):
    """Create an ActivityLogger instance"""
    return ActivityLogger(db_session)


@pytest.mark.asyncio
async def test_log_reaction_added(db_session, test_channel, activity_logger):
    """Test logging a reaction addition"""
    # Log a reaction
    await activity_logger.log_reaction_added(
        channel_id=test_channel.id,
        post_id=987654321,
        emoji="👍"
    )
    
    # Query the database to verify the log was created
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.post_id == 987654321
        )
    )
    log = result.scalar_one_or_none()
    
    # Verify the log entry
    assert log is not None
    assert log.channel_id == test_channel.id
    assert log.post_id == 987654321
    assert log.activity_type == "reaction_added"
    assert log.details["emoji"] == "👍"
    assert log.timestamp is not None
    # Verify timestamp is recent (within last minute)
    # Handle both timezone-aware and naive datetimes from SQLite
    now = datetime.now(timezone.utc)
    log_time = log.timestamp if log.timestamp.tzinfo else log.timestamp.replace(tzinfo=timezone.utc)
    time_diff = now - log_time
    assert time_diff.total_seconds() < 60


@pytest.mark.asyncio
async def test_log_boost_completed(db_session, test_channel, activity_logger):
    """Test logging boost completion"""
    # Log boost completion
    await activity_logger.log_boost_completed(
        channel_id=test_channel.id,
        post_id=987654321,
        reaction_count=5
    )
    
    # Query the database to verify the log was created
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.post_id == 987654321
        )
    )
    log = result.scalar_one_or_none()
    
    # Verify the log entry
    assert log is not None
    assert log.channel_id == test_channel.id
    assert log.post_id == 987654321
    assert log.activity_type == "boost_completed"
    assert log.details["reaction_count"] == 5
    assert log.timestamp is not None


@pytest.mark.asyncio
async def test_log_error_with_post_id(db_session, test_channel, activity_logger):
    """Test logging an error with a post_id"""
    # Log an error
    await activity_logger.log_error(
        channel_id=test_channel.id,
        post_id=987654321,
        error_type="rate_limit",
        details={"retry_after": 30, "message": "Too many requests"}
    )
    
    # Query the database to verify the log was created
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.post_id == 987654321
        )
    )
    log = result.scalar_one_or_none()
    
    # Verify the log entry
    assert log is not None
    assert log.channel_id == test_channel.id
    assert log.post_id == 987654321
    assert log.activity_type == "error"
    assert log.details["error_type"] == "rate_limit"
    assert log.details["retry_after"] == 30
    assert log.details["message"] == "Too many requests"
    assert log.timestamp is not None


@pytest.mark.asyncio
async def test_log_error_without_post_id(db_session, test_channel, activity_logger):
    """Test logging a channel-level error without post_id"""
    # Log an error without post_id
    await activity_logger.log_error(
        channel_id=test_channel.id,
        post_id=None,
        error_type="permission_error",
        details={"message": "Bot is not admin in channel"}
    )
    
    # Query the database to verify the log was created
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.post_id.is_(None)
        )
    )
    log = result.scalar_one_or_none()
    
    # Verify the log entry
    assert log is not None
    assert log.channel_id == test_channel.id
    assert log.post_id is None
    assert log.activity_type == "error"
    assert log.details["error_type"] == "permission_error"
    assert log.details["message"] == "Bot is not admin in channel"


@pytest.mark.asyncio
async def test_multiple_logs_for_same_post(db_session, test_channel, activity_logger):
    """Test logging multiple reactions for the same post"""
    post_id = 987654321
    emojis = ["👍", "❤️", "🔥"]
    
    # Log multiple reactions
    for emoji in emojis:
        await activity_logger.log_reaction_added(
            channel_id=test_channel.id,
            post_id=post_id,
            emoji=emoji
        )
    
    # Query all logs for this post
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.post_id == post_id,
            ActivityLog.activity_type == "reaction_added"
        )
    )
    logs = result.scalars().all()
    
    # Verify all reactions were logged
    assert len(logs) == 3
    logged_emojis = [log.details["emoji"] for log in logs]
    assert set(logged_emojis) == set(emojis)


@pytest.mark.asyncio
async def test_log_sequence_for_complete_boost(db_session, test_channel, activity_logger):
    """Test logging a complete boost sequence (reactions + completion)"""
    post_id = 987654321
    emojis = ["👍", "❤️", "🔥"]
    
    # Log individual reactions
    for emoji in emojis:
        await activity_logger.log_reaction_added(
            channel_id=test_channel.id,
            post_id=post_id,
            emoji=emoji
        )
    
    # Log boost completion
    await activity_logger.log_boost_completed(
        channel_id=test_channel.id,
        post_id=post_id,
        reaction_count=len(emojis)
    )
    
    # Query all logs for this post
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.post_id == post_id
        ).order_by(ActivityLog.timestamp)
    )
    logs = result.scalars().all()
    
    # Verify we have 4 logs (3 reactions + 1 completion)
    assert len(logs) == 4
    
    # Verify first 3 are reaction_added
    for i in range(3):
        assert logs[i].activity_type == "reaction_added"
    
    # Verify last one is boost_completed
    assert logs[3].activity_type == "boost_completed"
    assert logs[3].details["reaction_count"] == 3


@pytest.mark.asyncio
async def test_log_different_error_types(db_session, test_channel, activity_logger):
    """Test logging different types of errors"""
    error_scenarios = [
        ("permission_error", {"message": "Bot is not admin"}),
        ("rate_limit", {"retry_after": 30}),
        ("unknown_error", {"error": "Something went wrong", "emoji": "👍"}),
    ]
    
    # Log different error types
    for error_type, details in error_scenarios:
        await activity_logger.log_error(
            channel_id=test_channel.id,
            post_id=987654321,
            error_type=error_type,
            details=details
        )
    
    # Query all error logs
    result = await db_session.execute(
        select(ActivityLog).where(
            ActivityLog.channel_id == test_channel.id,
            ActivityLog.activity_type == "error"
        )
    )
    logs = result.scalars().all()
    
    # Verify all errors were logged
    assert len(logs) == 3
    error_types = [log.details["error_type"] for log in logs]
    assert "permission_error" in error_types
    assert "rate_limit" in error_types
    assert "unknown_error" in error_types


@pytest.mark.asyncio
async def test_logs_for_multiple_channels(db_session, activity_logger):
    """Test logging activities for multiple channels"""
    # Create two channels
    channel1 = Channel(
        channel_id=111111111,
        channel_title="Channel 1",
        mode="reaction"
    )
    channel2 = Channel(
        channel_id=222222222,
        channel_title="Channel 2",
        mode="reaction"
    )
    db_session.add(channel1)
    db_session.add(channel2)
    await db_session.commit()
    await db_session.refresh(channel1)
    await db_session.refresh(channel2)
    
    # Log activities for both channels
    await activity_logger.log_reaction_added(channel1.id, 100, "👍")
    await activity_logger.log_reaction_added(channel2.id, 200, "❤️")
    
    # Query logs for channel1
    result1 = await db_session.execute(
        select(ActivityLog).where(ActivityLog.channel_id == channel1.id)
    )
    logs1 = result1.scalars().all()
    
    # Query logs for channel2
    result2 = await db_session.execute(
        select(ActivityLog).where(ActivityLog.channel_id == channel2.id)
    )
    logs2 = result2.scalars().all()
    
    # Verify each channel has its own logs
    assert len(logs1) == 1
    assert len(logs2) == 1
    assert logs1[0].post_id == 100
    assert logs2[0].post_id == 200
    assert logs1[0].details["emoji"] == "👍"
    assert logs2[0].details["emoji"] == "❤️"


@pytest.mark.asyncio
async def test_timestamp_ordering(db_session, test_channel, activity_logger):
    """Test that logs are created with proper timestamp ordering"""
    # Log multiple activities
    await activity_logger.log_reaction_added(test_channel.id, 100, "👍")
    await activity_logger.log_reaction_added(test_channel.id, 100, "❤️")
    await activity_logger.log_boost_completed(test_channel.id, 100, 2)
    
    # Query logs ordered by timestamp
    result = await db_session.execute(
        select(ActivityLog)
        .where(ActivityLog.channel_id == test_channel.id)
        .order_by(ActivityLog.timestamp)
    )
    logs = result.scalars().all()
    
    # Verify timestamps are in order
    assert len(logs) == 3
    for i in range(len(logs) - 1):
        assert logs[i].timestamp <= logs[i + 1].timestamp
