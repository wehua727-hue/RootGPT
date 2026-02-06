"""
Channel model for storing channel configurations
"""

from typing import List, Optional
from sqlalchemy import Boolean, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Channel(Base, TimestampMixin):
    """Channel configuration model"""
    
    __tablename__ = "channels"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), nullable=False)
    discussion_group_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # AI Configuration
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_provider: Mapped[str] = mapped_column(String(50), default="openai")
    
    # Response Configuration
    daily_limit: Mapped[int] = mapped_column(Integer, default=100)
    rate_limit_minutes: Mapped[int] = mapped_column(Integer, default=5)
    
    # Trigger words (stored as JSON array)
    trigger_words: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Admin users (stored as JSON array)
    admin_user_ids: Mapped[List[int]] = mapped_column(JSON, default=list)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    comments = relationship("Comment", back_populates="channel", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="channel", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="channel", cascade="all, delete-orphan")
    statistics = relationship("Statistics", back_populates="channel", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, channel_id={self.channel_id}, title='{self.channel_title}')>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "discussion_group_id": self.discussion_group_id,
            "ai_enabled": self.ai_enabled,
            "ai_provider": self.ai_provider,
            "daily_limit": self.daily_limit,
            "rate_limit_minutes": self.rate_limit_minutes,
            "trigger_words": self.trigger_words,
            "admin_user_ids": self.admin_user_ids,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }