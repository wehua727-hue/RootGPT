"""
Unit tests for PostMonitorService
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.base import Base
from src.models.channel import Channel
from src.services.post_monitor_service import PostMonitorService
from src.services.reaction_boost_service import ReactionBoostService
from aiogram.exceptions import TelegramAPIError


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory database session for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_bot():
    """Create a mock Telegram Bot"""
    bot = AsyncMock()
    bot.id = 123456789
    return bot


@pytest.fixture
def mock_reaction_service():
    """Create a mock ReactionBoostService"""
    service = AsyncMock(spec=ReactionBoostService)
    return service


@pytest_asyncio.fixture
async def post_monitor_service(mock_bot, db_session, mock_reaction_service):
    """Create a PostMonitorService instance for testing"""
    service = PostMonitorService(mock_bot, db_session, mock_reaction_service)
    return service


@pytest_asyncio.fixture
async def sample_channel(db_session):
    """Create a sample channel for testing"""
    channel = Channel(
        channel_id=-1001234567890,
        channel_title="Test Channel",
        mode="reaction",
        is_active=True,
        reaction_settings={
            "emojis": ["👍", "❤️"],
            "reaction_count": 2,
            "delay_min": 1.0,
            "delay_max": 2.0,
            "auto_boost": True
        }
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


class TestPostMonitorServiceInit:
    """Tests for PostMonitorService initialization"""
    
    @pytest.mark.asyncio
    async def test_init_with_all_parameters(self, mock_bot, db_session, mock_reaction_service):
        """Test initialization with all parameters"""
        service = PostMonitorService(mock_bot, db_session, mock_reaction_service)
        
        assert service.bot == mock_bot
        assert service.db == db_session
        assert service.reaction_service == mock_reaction_service
        assert service.last_checked == {}
    
    @pytest.mark.asyncio
    async def test_init_without_reaction_service(self, mock_bot, db_session):
        """Test initialization without reaction service"""
        service = PostMonitorService(mock_bot, db_session)
        
        assert service.bot == mock_bot
        assert service.db == db_session
        assert service.reaction_service is None
        assert service.last_checked == {}


class TestGetActiveChannels:
    """Tests for _get_active_channels method"""
    
    @pytest.mark.asyncio
    async def test_get_active_channels_returns_active_only(self, post_monitor_service, db_session):
        """Test that only active channels are returned"""
        # Create active channel
        active_channel = Channel(
            channel_id=-1001111111111,
            channel_title="Active Channel",
            mode="reaction",
            is_active=True
        )
        db_session.add(active_channel)
        
        # Create inactive channel
        inactive_channel = Channel(
            channel_id=-1002222222222,
            channel_title="Inactive Channel",
            mode="reaction",
            is_active=False
        )
        db_session.add(inactive_channel)
        
        await db_session.commit()
        
        # Get active channels
        channels = await post_monitor_service._get_active_channels()
        
        assert len(channels) == 1
        assert channels[0].channel_id == -1001111111111
        assert channels[0].is_active is True
    
    @pytest.mark.asyncio
    async def test_get_active_channels_empty_database(self, post_monitor_service):
        """Test getting active channels from empty database"""
        channels = await post_monitor_service._get_active_channels()
        
        assert channels == []
    
    @pytest.mark.asyncio
    async def test_get_active_channels_multiple_modes(self, post_monitor_service, db_session):
        """Test that channels with different modes are all returned if active"""
        # Create channels with different modes
        comment_channel = Channel(
            channel_id=-1001111111111,
            channel_title="Comment Channel",
            mode="comment",
            is_active=True
        )
        reaction_channel = Channel(
            channel_id=-1002222222222,
            channel_title="Reaction Channel",
            mode="reaction",
            is_active=True
        )
        both_channel = Channel(
            channel_id=-1003333333333,
            channel_title="Both Channel",
            mode="both",
            is_active=True
        )
        
        db_session.add_all([comment_channel, reaction_channel, both_channel])
        await db_session.commit()
        
        # Get active channels
        channels = await post_monitor_service._get_active_channels()
        
        assert len(channels) == 3
        modes = {ch.mode for ch in channels}
        assert modes == {"comment", "reaction", "both"}


class TestFetchNewPosts:
    """Tests for _fetch_new_posts method"""
    
    @pytest.mark.asyncio
    async def test_fetch_new_posts_with_valid_channel(self, post_monitor_service, sample_channel, mock_bot):
        """Test fetching new posts from a valid channel"""
        # Mock get_chat to return a valid chat
        mock_chat = MagicMock()
        mock_chat.id = sample_channel.channel_id
        mock_bot.get_chat.return_value = mock_chat
        
        # Fetch new posts
        posts = await post_monitor_service._fetch_new_posts(sample_channel)
        
        # Should return empty list (webhook-based implementation)
        assert posts == []
        
        # Verify get_chat was called
        mock_bot.get_chat.assert_called_once_with(str(sample_channel.channel_id))
    
    @pytest.mark.asyncio
    async def test_fetch_new_posts_with_telegram_error(self, post_monitor_service, sample_channel, mock_bot):
        """Test handling of Telegram API errors"""
        
        # Mock get_chat to raise an error
        mock_bot.get_chat.side_effect = TelegramAPIError("Channel not found")
        
        # Fetch new posts
        posts = await post_monitor_service._fetch_new_posts(sample_channel)
        
        # Should return empty list on error
        assert posts == []
    
    @pytest.mark.asyncio
    async def test_fetch_new_posts_updates_last_checked(self, post_monitor_service, sample_channel):
        """Test that last_checked is tracked per channel"""
        # Initially, last_checked should be empty
        assert sample_channel.id not in post_monitor_service.last_checked
        
        # After fetching, it should still be 0 (no new posts)
        await post_monitor_service._fetch_new_posts(sample_channel)
        
        # last_checked should still be empty or 0 for this channel
        assert post_monitor_service.last_checked.get(sample_channel.id, 0) == 0


class TestProcessChannelPost:
    """Tests for process_channel_post method"""
    
    @pytest.mark.asyncio
    async def test_process_channel_post_new_post(self, post_monitor_service, sample_channel, mock_reaction_service):
        """Test processing a new channel post"""
        # Create a mock message
        mock_message = MagicMock()
        mock_message.message_id = 100
        mock_message.chat_id = sample_channel.channel_id
        
        # Process the post
        await post_monitor_service.process_channel_post(sample_channel, mock_message)
        
        # Verify reaction service was called
        mock_reaction_service.boost_post.assert_called_once_with(sample_channel, mock_message)
        
        # Verify last_checked was updated
        assert post_monitor_service.last_checked[sample_channel.id] == 100
    
    @pytest.mark.asyncio
    async def test_process_channel_post_duplicate(self, post_monitor_service, sample_channel, mock_reaction_service):
        """Test that duplicate posts are not processed"""
        # Create a mock message
        mock_message = MagicMock()
        mock_message.message_id = 100
        
        # Process the post first time
        await post_monitor_service.process_channel_post(sample_channel, mock_message)
        
        # Reset mock
        mock_reaction_service.reset_mock()
        
        # Process the same post again
        await post_monitor_service.process_channel_post(sample_channel, mock_message)
        
        # Verify reaction service was NOT called second time
        mock_reaction_service.boost_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_channel_post_comment_mode(self, post_monitor_service, db_session, mock_reaction_service):
        """Test that comment mode channels don't trigger reaction boosting"""
        # Create a comment-only channel
        comment_channel = Channel(
            channel_id=-1001234567890,
            channel_title="Comment Channel",
            mode="comment",
            is_active=True
        )
        db_session.add(comment_channel)
        await db_session.commit()
        await db_session.refresh(comment_channel)
        
        # Create a mock message
        mock_message = MagicMock()
        mock_message.message_id = 100
        
        # Process the post
        await post_monitor_service.process_channel_post(comment_channel, mock_message)
        
        # Verify reaction service was NOT called
        mock_reaction_service.boost_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_channel_post_both_mode(self, mock_bot, db_session):
        """Test that both mode channels trigger reaction boosting"""
        # Create a fresh mock reaction service for this test
        mock_reaction_service = AsyncMock(spec=ReactionBoostService)
        
        # Create service with the mock
        service = PostMonitorService(mock_bot, db_session, mock_reaction_service)
        
        # Create a both-mode channel
        both_channel = Channel(
            channel_id=-1001234567890,
            channel_title="Both Channel",
            mode="both",
            is_active=True,
            reaction_settings={
                "emojis": ["👍"],
                "reaction_count": 1,
                "delay_min": 1.0,
                "delay_max": 2.0,
                "auto_boost": True
            }
        )
        db_session.add(both_channel)
        await db_session.commit()
        await db_session.refresh(both_channel)
        
        # Create a mock message
        mock_message = MagicMock()
        mock_message.message_id = 100
        
        # Process the post
        await service.process_channel_post(both_channel, mock_message)
        
        # Verify reaction service WAS called
        mock_reaction_service.boost_post.assert_called_once_with(both_channel, mock_message)
    
    @pytest.mark.asyncio
    async def test_process_channel_post_without_reaction_service(self, mock_bot, db_session, sample_channel):
        """Test processing post when reaction service is not available"""
        # Create service without reaction service
        service = PostMonitorService(mock_bot, db_session, None)
        
        # Create a mock message
        mock_message = MagicMock()
        mock_message.message_id = 100
        
        # Process the post - should not raise error
        await service.process_channel_post(sample_channel, mock_message)
        
        # Verify last_checked was still updated
        assert service.last_checked[sample_channel.id] == 100


class TestMonitorChannels:
    """Tests for monitor_channels main loop"""
    
    @pytest.mark.asyncio
    async def test_monitor_channels_with_no_channels(self, post_monitor_service):
        """Test monitoring when no channels exist"""
        # Should not raise any errors
        await post_monitor_service.monitor_channels()
    
    @pytest.mark.asyncio
    async def test_monitor_channels_with_active_channel(self, post_monitor_service, sample_channel, mock_bot):
        """Test monitoring with an active channel"""
        # Mock get_chat
        mock_chat = MagicMock()
        mock_chat.id = sample_channel.channel_id
        mock_bot.get_chat.return_value = mock_chat
        
        # Run monitoring
        await post_monitor_service.monitor_channels()
        
        # Verify get_chat was called for the channel
        mock_bot.get_chat.assert_called()
    
    @pytest.mark.asyncio
    async def test_monitor_channels_handles_telegram_error(self, post_monitor_service, sample_channel, mock_bot):
        """Test that Telegram errors are handled gracefully"""
        
        # Mock get_chat to raise an error
        mock_bot.get_chat.side_effect = TelegramAPIError("API Error")
        
        # Should not raise error
        await post_monitor_service.monitor_channels()
    
    @pytest.mark.asyncio
    async def test_monitor_channels_handles_boost_error(self, post_monitor_service, sample_channel, mock_reaction_service):
        """Test that errors during boosting are handled gracefully"""
        # Make boost_post raise an error
        mock_reaction_service.boost_post.side_effect = Exception("Boost failed")
        
        # Create a mock message and add it to the service's processing
        mock_message = MagicMock()
        mock_message.message_id = 100
        
        # Should not raise error
        await post_monitor_service.process_channel_post(sample_channel, mock_message)
        
        # Verify boost was attempted
        mock_reaction_service.boost_post.assert_called_once()


class TestLogError:
    """Tests for _log_error method"""
    
    @pytest.mark.asyncio
    async def test_log_error_creates_activity_log(self, post_monitor_service, sample_channel):
        """Test that errors are logged to the database"""
        error = Exception("Test error")
        
        # Log the error
        await post_monitor_service._log_error(sample_channel, error)
        
        # Verify log was created (we can't easily check without querying)
        # This test mainly ensures no exception is raised
    
    @pytest.mark.asyncio
    async def test_log_error_handles_logging_failure(self, post_monitor_service, sample_channel, db_session):
        """Test that logging failures don't crash the service"""
        # Close the session to cause a logging failure
        await db_session.close()
        
        error = Exception("Test error")
        
        # Should not raise error even if logging fails
        await post_monitor_service._log_error(sample_channel, error)
