"""
Response model for storing bot responses
"""

from enum import Enum
from typing import Optional
from sqlalchemy import Boolean, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ResponseType(Enum):
    """Response type enumeration"""
    TEMPLATE = "template"
    AI_GENERATED = "ai_generated"
    FALLBACK = "fallback"


class Response(Base, TimestampMixin):
    """Response model for storing bot responses"""
    
    __tablename__ = "responses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_type: Mapped[ResponseType] = mapped_column(
        SQLEnum(ResponseType), 
        nullable=False
    )
    
    # AI provider used (if AI generated)
    ai_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Delivery status
    sent_successfully: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Foreign keys
    comment_id: Mapped[int] = mapped_column(Integer, ForeignKey("comments.id"), nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"), nullable=False)
    
    # Relationships
    comment = relationship("Comment", back_populates="responses")
    channel = relationship("Channel", back_populates="responses")
    
    def __repr__(self) -> str:
        return f"<Response(id={self.id}, type={self.response_type.value}, sent={self.sent_successfully})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "response_text": self.response_text,
            "response_type": self.response_type.value,
            "ai_provider": self.ai_provider,
            "sent_successfully": self.sent_successfully,
            "telegram_message_id": self.telegram_message_id,
            "error_message": self.error_message,
            "comment_id": self.comment_id,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }