"""
ActivityLog model for tracking reaction boost activities
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ActivityLog(Base):
    """Model for logging reaction boost activities and errors"""
    
    __tablename__ = "activity_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False
    )
    post_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Relationship to Channel
    channel = relationship("Channel", back_populates="activity_logs")
    
    # Create index on (channel_id, timestamp) for efficient queries
    __table_args__ = (
        Index('idx_channel_timestamp', 'channel_id', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<ActivityLog(id={self.id}, channel_id={self.channel_id}, activity_type='{self.activity_type}')>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "post_id": self.post_id,
            "activity_type": self.activity_type,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
