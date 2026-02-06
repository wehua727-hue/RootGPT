"""
Statistics model for tracking bot performance
"""

from datetime import date
from sqlalchemy import Date, Integer, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .comment import CommentCategory


class Statistics(Base, TimestampMixin):
    """Statistics model for tracking daily metrics"""
    
    __tablename__ = "statistics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Metrics
    comments_received: Mapped[int] = mapped_column(Integer, default=0)
    responses_sent: Mapped[int] = mapped_column(Integer, default=0)
    ai_responses: Mapped[int] = mapped_column(Integer, default=0)
    template_responses: Mapped[int] = mapped_column(Integer, default=0)
    
    # Category breakdown
    category: Mapped[CommentCategory] = mapped_column(
        SQLEnum(CommentCategory), 
        nullable=False
    )
    category_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Foreign keys
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"), nullable=False)
    
    # Relationships
    channel = relationship("Channel", back_populates="statistics")
    
    def __repr__(self) -> str:
        return f"<Statistics(id={self.id}, date={self.stat_date}, channel_id={self.channel_id})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "stat_date": self.stat_date.isoformat() if self.stat_date else None,
            "comments_received": self.comments_received,
            "responses_sent": self.responses_sent,
            "ai_responses": self.ai_responses,
            "template_responses": self.template_responses,
            "category": self.category.value,
            "category_count": self.category_count,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }