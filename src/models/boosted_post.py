"""
BoostedPost model for tracking reaction-boosted posts
"""

from datetime import datetime
from typing import List
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class BoostedPost(Base):
    """Model for tracking posts that have been reaction-boosted"""
    
    __tablename__ = "boosted_posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False
    )
    post_id: Mapped[int] = mapped_column(Integer, nullable=False)
    boost_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    emojis_used: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Relationship to Channel
    channel = relationship("Channel", back_populates="boosted_posts")
    
    # Create unique index on (channel_id, post_id)
    __table_args__ = (
        Index('idx_channel_post', 'channel_id', 'post_id', unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<BoostedPost(id={self.id}, channel_id={self.channel_id}, post_id={self.post_id})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "post_id": self.post_id,
            "boost_timestamp": self.boost_timestamp.isoformat() if self.boost_timestamp else None,
            "reaction_count": self.reaction_count,
            "emojis_used": self.emojis_used
        }
