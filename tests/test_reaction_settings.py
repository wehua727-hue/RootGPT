"""
Unit tests for ReactionSettings dataclass
"""

import pytest
from src.models.reaction_settings import ReactionSettings


class TestReactionSettingsValidation:
    """Test validation logic for ReactionSettings"""
    
    def test_valid_settings(self):
        """Test that valid settings pass validation"""
        settings = ReactionSettings(
            emojis=["👍", "❤️", "🔥"],
            reaction_count=3,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is True
        assert error is None
    
    def test_empty_emoji_list(self):
        """Test that empty emoji list is rejected (Requirement 2.6)"""
        settings = ReactionSettings(
            emojis=[],
            reaction_count=1,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "at least one emoji" in error.lower()
    
    def test_reaction_count_zero(self):
        """Test that reaction count of 0 is rejected (Requirement 2.7)"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=0,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "between 1 and 100" in error.lower()
    
    def test_reaction_count_one(self):
        """Test that reaction count of 1 is valid (Requirement 2.7)"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=1,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is True
        assert error is None
    
    def test_reaction_count_hundred(self):
        """Test that reaction count of 100 is valid (Requirement 2.7)"""
        # Create 100 emojis
        emojis = [f"emoji_{i}" for i in range(100)]
        settings = ReactionSettings(
            emojis=emojis,
            reaction_count=100,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is True
        assert error is None
    
    def test_reaction_count_over_hundred(self):
        """Test that reaction count over 100 is rejected (Requirement 2.7)"""
        # Create 101 emojis
        emojis = [f"emoji_{i}" for i in range(101)]
        settings = ReactionSettings(
            emojis=emojis,
            reaction_count=101,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "between 1 and 100" in error.lower()
    
    def test_negative_delay_min(self):
        """Test that negative minimum delay is rejected (Requirement 2.8)"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=1,
            delay_min=-1.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "non-negative" in error.lower()
    
    def test_delay_max_less_than_min(self):
        """Test that max delay less than min delay is rejected (Requirement 2.8)"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=1,
            delay_min=8.0,
            delay_max=2.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "greater than or equal to minimum" in error.lower()
    
    def test_delay_max_equal_to_min(self):
        """Test that max delay equal to min delay is valid (Requirement 2.8)"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=1,
            delay_min=5.0,
            delay_max=5.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is True
        assert error is None
    
    def test_reaction_count_exceeds_emoji_count(self):
        """Test that reaction count exceeding emoji count is rejected"""
        settings = ReactionSettings(
            emojis=["👍", "❤️"],
            reaction_count=3,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "cannot exceed number of emojis" in error.lower()
    
    def test_reaction_count_equals_emoji_count(self):
        """Test that reaction count equal to emoji count is valid"""
        settings = ReactionSettings(
            emojis=["👍", "❤️", "🔥"],
            reaction_count=3,
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is True
        assert error is None
    
    def test_non_integer_reaction_count(self):
        """Test that non-integer reaction count is rejected"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=2.5,  # type: ignore
            delay_min=2.0,
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "must be an integer" in error.lower()
    
    def test_non_numeric_delay(self):
        """Test that non-numeric delay values are rejected"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=1,
            delay_min="two",  # type: ignore
            delay_max=8.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is False
        assert "must be numbers" in error.lower()
    
    def test_zero_delays(self):
        """Test that zero delays are valid (Requirement 2.8)"""
        settings = ReactionSettings(
            emojis=["👍"],
            reaction_count=1,
            delay_min=0.0,
            delay_max=0.0,
            auto_boost=True
        )
        is_valid, error = settings.validate()
        assert is_valid is True
        assert error is None


class TestReactionSettingsConversion:
    """Test dictionary conversion methods"""
    
    def test_from_dict(self):
        """Test creating ReactionSettings from dictionary"""
        data = {
            'emojis': ["👍", "❤️"],
            'reaction_count': 2,
            'delay_min': 3.0,
            'delay_max': 7.0,
            'auto_boost': False
        }
        settings = ReactionSettings.from_dict(data)
        assert settings.emojis == ["👍", "❤️"]
        assert settings.reaction_count == 2
        assert settings.delay_min == 3.0
        assert settings.delay_max == 7.0
        assert settings.auto_boost is False
    
    def test_from_dict_with_defaults(self):
        """Test creating ReactionSettings from dictionary with missing fields"""
        data = {}
        settings = ReactionSettings.from_dict(data)
        assert settings.emojis == []
        assert settings.reaction_count == 1
        assert settings.delay_min == 2.0
        assert settings.delay_max == 8.0
        assert settings.auto_boost is True
    
    def test_to_dict(self):
        """Test converting ReactionSettings to dictionary"""
        settings = ReactionSettings(
            emojis=["👍", "❤️", "🔥"],
            reaction_count=3,
            delay_min=2.5,
            delay_max=9.0,
            auto_boost=True
        )
        data = settings.to_dict()
        assert data == {
            'emojis': ["👍", "❤️", "🔥"],
            'reaction_count': 3,
            'delay_min': 2.5,
            'delay_max': 9.0,
            'auto_boost': True
        }
    
    def test_round_trip_conversion(self):
        """Test that from_dict and to_dict are inverses"""
        original_data = {
            'emojis': ["😍", "🎉"],
            'reaction_count': 5,
            'delay_min': 1.0,
            'delay_max': 10.0,
            'auto_boost': False
        }
        settings = ReactionSettings.from_dict(original_data)
        converted_data = settings.to_dict()
        assert converted_data == original_data
