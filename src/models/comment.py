"""
Comment model for storing processed comments
"""

from enum import Enum
from typing import Optional
from sqlalchemy import Boolean, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class CommentCategory(Enum):
    """Comment category enumeration"""
    PRICE = "price"
    LOCATION = "location"
    CONTACT = "contact"
    ORDER = "order"
    GENERAL = "general"


class Comment(Base, TimestampMixin):
    """Comment model for storing user comments"""
    
    __tablename__ = "comments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[CommentCategory] = mapped_column(
        SQLEnum(CommentCategory), 
        default=CommentCategory.GENERAL
    )
    
    # Processing status
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    should_respond: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Foreign keys
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"), nullable=False)
    
    # Relationships
    channel = relationship("Channel", back_populates="comments")
    responses = relationship("Response", back_populates="comment", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, user_id={self.user_id}, category={self.category.value})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "username": self.username,
            "text": self.text,
            "category": self.category.value,
            "processed": self.processed,
            "should_respond": self.should_respond,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }