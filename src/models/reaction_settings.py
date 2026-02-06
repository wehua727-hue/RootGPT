"""
ReactionSettings dataclass for reaction boost configuration
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReactionSettings:
    """
    Configuration settings for reaction boosting on channel posts.
    
    Attributes:
        emojis: List of emoji strings to use for reactions
        reaction_count: Number of reactions to add per post (1-100)
        delay_min: Minimum delay in seconds between reactions
        delay_max: Maximum delay in seconds between reactions
        auto_boost: Whether to automatically boost new posts
    """
    emojis: list[str]
    reaction_count: int
    delay_min: float
    delay_max: float
    auto_boost: bool
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the reaction settings.
        
        Returns:
            A tuple of (is_valid, error_message).
            If valid, returns (True, None).
            If invalid, returns (False, error_message).
        
        Validation rules:
        - At least one emoji must be selected (Requirement 2.6)
        - Reaction count must be between 1 and 100 (Requirement 2.7)
        - Delay range must contain valid positive numbers (Requirement 2.8)
        - Reaction count cannot exceed number of available emojis
        """
        # Requirement 2.6: At least one emoji must be selected
        if not self.emojis:
            return False, "At least one emoji must be selected"
        
        # Requirement 2.7: Reaction count must be between 1 and 100
        if not isinstance(self.reaction_count, int):
            return False, "Reaction count must be an integer"
        
        if not (1 <= self.reaction_count <= 100):
            return False, "Reaction count must be between 1 and 100"
        
        # Requirement 2.8: Delay range must contain valid positive numbers
        if not isinstance(self.delay_min, (int, float)) or not isinstance(self.delay_max, (int, float)):
            return False, "Delay values must be numbers"
        
        if self.delay_min < 0:
            return False, "Minimum delay must be non-negative"
        
        if self.delay_max < self.delay_min:
            return False, "Maximum delay must be greater than or equal to minimum delay"
        
        # Additional validation: reaction count cannot exceed number of emojis
        if self.reaction_count > len(self.emojis):
            return False, "Reaction count cannot exceed number of emojis"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ReactionSettings':
        """
        Create a ReactionSettings instance from a dictionary.
        
        Args:
            data: Dictionary containing reaction settings data
            
        Returns:
            ReactionSettings instance
        """
        return cls(
            emojis=data.get('emojis', []),
            reaction_count=data.get('reaction_count', 1),
            delay_min=data.get('delay_min', 2.0),
            delay_max=data.get('delay_max', 8.0),
            auto_boost=data.get('auto_boost', True)
        )
    
    def to_dict(self) -> dict:
        """
        Convert the ReactionSettings instance to a dictionary.
        
        Returns:
            Dictionary representation of the settings
        """
        return {
            'emojis': self.emojis,
            'reaction_count': self.reaction_count,
            'delay_min': self.delay_min,
            'delay_max': self.delay_max,
            'auto_boost': self.auto_boost
        }
