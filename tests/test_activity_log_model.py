"""
Tests for ActivityLog model
"""

import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from src.models import Base, Channel, ActivityLog


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


@pytest.mark.asyncio
async def test_activity_log_creation(db_session):
    """Test creating an ActivityLog record"""
    # Create a channel first
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create an activity log
    activity_log = ActivityLog(
        channel_id=channel.id,
        post_id=987654321,
        activity_type="reaction_added",
        details={"emoji": "👍"},
        timestamp=datetime.utcnow()
    )
    db_session.add(activity_log)
    await db_session.commit()
    await db_session.refresh(activity_log)
    
    # Verify the record was created
    assert activity_log.id is not None
    assert activity_log.channel_id == channel.id
    assert activity_log.post_id == 987654321
    assert activity_log.activity_type == "reaction_added"
    assert activity_log.details["emoji"] == "👍"
    assert activity_log.timestamp is not None


@pytest.mark.asyncio
async def test_activity_log_with_null_post_id(db_session):
    """Test creating an ActivityLog with null post_id (for channel-level errors)"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create an activity log without post_id
    activity_log = ActivityLog(
        channel_id=channel.id,
        post_id=None,  # No specific post
        activity_type="error",
        details={"error_type": "permission_error", "message": "Bot is not admin"},
        timestamp=datetime.utcnow()
    )
    db_session.add(activity_log)
    await db_session.commit()
    await db_session.refresh(activity_log)
    
    # Verify the record was created with null post_id
    assert activity_log.id is not None
    assert activity_log.post_id is None
    assert activity_log.activity_type == "error"


@pytest.mark.asyncio
async def test_activity_log_relationship(db_session):
    """Test the relationship between ActivityLog and Channel"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create multiple activity logs
    for i in range(3):
        activity_log = ActivityLog(
            channel_id=channel.id,
            post_id=100 + i,
            activity_type="reaction_added",
            details={"emoji": "👍"},
            timestamp=datetime.utcnow()
        )
        db_session.add(activity_log)
    
    await db_session.commit()
    
    # Query activity logs for this channel
    result = await db_session.execute(
        select(ActivityLog).where(ActivityLog.channel_id == channel.id)
    )
    activity_logs = result.scalars().all()
    
    # Verify we have 3 activity logs
    assert len(activity_logs) == 3


@pytest.mark.asyncio
async def test_activity_log_to_dict(db_session):
    """Test the to_dict method of ActivityLog"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create an activity log
    timestamp = datetime.utcnow()
    activity_log = ActivityLog(
        channel_id=channel.id,
        post_id=987654321,
        activity_type="boost_completed",
        details={"reaction_count": 5},
        timestamp=timestamp
    )
    db_session.add(activity_log)
    await db_session.commit()
    await db_session.refresh(activity_log)
    
    # Convert to dict
    log_dict = activity_log.to_dict()
    
    # Verify the dictionary
    assert log_dict["id"] == activity_log.id
    assert log_dict["channel_id"] == channel.id
    assert log_dict["post_id"] == 987654321
    assert log_dict["activity_type"] == "boost_completed"
    assert log_dict["details"]["reaction_count"] == 5
    assert log_dict["timestamp"] == timestamp.isoformat()


@pytest.mark.asyncio
async def test_activity_log_cascade_delete(db_session):
    """Test that activity logs are deleted when channel is deleted"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create an activity log
    activity_log = ActivityLog(
        channel_id=channel.id,
        post_id=987654321,
        activity_type="reaction_added",
        details={"emoji": "👍"},
        timestamp=datetime.utcnow()
    )
    db_session.add(activity_log)
    await db_session.commit()
    
    # Delete the channel
    await db_session.delete(channel)
    await db_session.commit()
    
    # Verify activity log was also deleted (cascade)
    result = await db_session.execute(
        select(ActivityLog).where(ActivityLog.post_id == 987654321)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_activity_log_index_query(db_session):
    """Test querying activity logs using the (channel_id, timestamp) index"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create activity logs with different timestamps
    timestamps = []
    for i in range(5):
        timestamp = datetime.utcnow()
        timestamps.append(timestamp)
        activity_log = ActivityLog(
            channel_id=channel.id,
            post_id=100 + i,
            activity_type="reaction_added",
            details={"emoji": "👍"},
            timestamp=timestamp
        )
        db_session.add(activity_log)
    
    await db_session.commit()
    
    # Query logs ordered by timestamp (descending)
    result = await db_session.execute(
        select(ActivityLog)
        .where(ActivityLog.channel_id == channel.id)
        .order_by(ActivityLog.timestamp.desc())
    )
    logs = result.scalars().all()
    
    # Verify we got all logs in descending order
    assert len(logs) == 5
    for i in range(len(logs) - 1):
        assert logs[i].timestamp >= logs[i + 1].timestamp


@pytest.mark.asyncio
async def test_activity_log_different_types(db_session):
    """Test creating activity logs with different activity types"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create logs with different activity types
    activity_types = [
        ("reaction_added", {"emoji": "👍"}),
        ("boost_completed", {"reaction_count": 5}),
        ("error", {"error_type": "rate_limit", "retry_after": 30})
    ]
    
    for activity_type, details in activity_types:
        activity_log = ActivityLog(
            channel_id=channel.id,
            post_id=987654321,
            activity_type=activity_type,
            details=details,
            timestamp=datetime.utcnow()
        )
        db_session.add(activity_log)
    
    await db_session.commit()
    
    # Query and verify all types were created
    result = await db_session.execute(
        select(ActivityLog).where(ActivityLog.channel_id == channel.id)
    )
    logs = result.scalars().all()
    
    assert len(logs) == 3
    log_types = [log.activity_type for log in logs]
    assert "reaction_added" in log_types
    assert "boost_completed" in log_types
    assert "error" in log_types
