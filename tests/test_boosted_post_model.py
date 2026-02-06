"""
Tests for BoostedPost model
"""

import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from src.models import Base, Channel, BoostedPost


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
async def test_boosted_post_creation(db_session):
    """Test creating a BoostedPost record"""
    # Create a channel first
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create a boosted post
    boosted_post = BoostedPost(
        channel_id=channel.id,
        post_id=987654321,
        boost_timestamp=datetime.utcnow(),
        reaction_count=5,
        emojis_used=["👍", "❤️", "🔥", "😍", "🎉"]
    )
    db_session.add(boosted_post)
    await db_session.commit()
    await db_session.refresh(boosted_post)
    
    # Verify the record was created
    assert boosted_post.id is not None
    assert boosted_post.channel_id == channel.id
    assert boosted_post.post_id == 987654321
    assert boosted_post.reaction_count == 5
    assert len(boosted_post.emojis_used) == 5
    assert "👍" in boosted_post.emojis_used


@pytest.mark.asyncio
async def test_boosted_post_unique_constraint(db_session):
    """Test that the unique constraint on (channel_id, post_id) works"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create first boosted post
    boosted_post1 = BoostedPost(
        channel_id=channel.id,
        post_id=111,
        boost_timestamp=datetime.utcnow(),
        reaction_count=3,
        emojis_used=["👍", "❤️", "🔥"]
    )
    db_session.add(boosted_post1)
    await db_session.commit()
    
    # Try to create duplicate boosted post (same channel_id and post_id)
    boosted_post2 = BoostedPost(
        channel_id=channel.id,
        post_id=111,  # Same post_id
        boost_timestamp=datetime.utcnow(),
        reaction_count=2,
        emojis_used=["😍", "🎉"]
    )
    db_session.add(boosted_post2)
    
    # This should raise an integrity error
    with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_boosted_post_relationship(db_session):
    """Test the relationship between BoostedPost and Channel"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create multiple boosted posts
    for i in range(3):
        boosted_post = BoostedPost(
            channel_id=channel.id,
            post_id=100 + i,
            boost_timestamp=datetime.utcnow(),
            reaction_count=2,
            emojis_used=["👍", "❤️"]
        )
        db_session.add(boosted_post)
    
    await db_session.commit()
    
    # Query boosted posts for this channel
    result = await db_session.execute(
        select(BoostedPost).where(BoostedPost.channel_id == channel.id)
    )
    boosted_posts = result.scalars().all()
    
    # Verify we have 3 boosted posts
    assert len(boosted_posts) == 3


@pytest.mark.asyncio
async def test_boosted_post_to_dict(db_session):
    """Test the to_dict method of BoostedPost"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create a boosted post
    timestamp = datetime.utcnow()
    boosted_post = BoostedPost(
        channel_id=channel.id,
        post_id=987654321,
        boost_timestamp=timestamp,
        reaction_count=4,
        emojis_used=["👍", "❤️", "🔥", "😍"]
    )
    db_session.add(boosted_post)
    await db_session.commit()
    await db_session.refresh(boosted_post)
    
    # Convert to dict
    post_dict = boosted_post.to_dict()
    
    # Verify the dictionary
    assert post_dict["id"] == boosted_post.id
    assert post_dict["channel_id"] == channel.id
    assert post_dict["post_id"] == 987654321
    assert post_dict["reaction_count"] == 4
    assert len(post_dict["emojis_used"]) == 4
    assert post_dict["boost_timestamp"] == timestamp.isoformat()


@pytest.mark.asyncio
async def test_boosted_post_cascade_delete(db_session):
    """Test that boosted posts are deleted when channel is deleted"""
    # Create a channel
    channel = Channel(
        channel_id=123456789,
        channel_title="Test Channel",
        mode="reaction"
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    
    # Create a boosted post
    boosted_post = BoostedPost(
        channel_id=channel.id,
        post_id=987654321,
        boost_timestamp=datetime.utcnow(),
        reaction_count=3,
        emojis_used=["👍", "❤️", "🔥"]
    )
    db_session.add(boosted_post)
    await db_session.commit()
    
    # Delete the channel
    await db_session.delete(channel)
    await db_session.commit()
    
    # Verify boosted post was also deleted (cascade)
    result = await db_session.execute(
        select(BoostedPost).where(BoostedPost.post_id == 987654321)
    )
    assert result.scalar_one_or_none() is None
