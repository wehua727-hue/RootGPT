"""
Blacklist model for spam protection
"""

from enum import Enum
from typing import Optional
from sqlalchemy import Boolean, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class BlacklistType(Enum):
    """Blacklist entry type"""
    USER = "user"
    KEYWORD = "keyword"
    PATTERN = "pattern"


class Blacklist(Base, TimestampMixin):
    """Blacklist model for spam protection"""
    
    __tablename__ = "blacklist"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_type: Mapped[BlacklistType] = mapped_column(
        SQLEnum(BlacklistType), 
        nullable=False
    )
    
    # Entry data
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    keyword: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Global or channel-specific (None = global)
    channel_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Blacklist(id={self.id}, type={self.entry_type.value}, active={self.is_active})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "entry_type": self.entry_type.value,
            "user_id": self.user_id,
            "keyword": self.keyword,
            "pattern": self.pattern,
            "is_active": self.is_active,
            "reason": self.reason,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }