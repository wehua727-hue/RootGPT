"""
RepostStats model for aggregated statistics per source channel
"""

from sqlalchemy import Column, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import Base, TimestampMixin


class RepostStats(Base, TimestampMixin):
    """Aggregated statistics per source channel"""
    
    __tablename__ = "repost_stats"
    
    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey('repost_configs.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    total_reposts = Column(Integer, default=0, nullable=False)
    successful_reposts = Column(Integer, default=0, nullable=False)
    failed_reposts = Column(Integer, default=0, nullable=False)
    filtered_posts = Column(Integer, default=0, nullable=False)
    
    # Content type breakdown (JSON)
    content_type_counts = Column(JSON, default=dict, nullable=False)  # {'photo': 10, 'video': 5}
    
    last_repost_at = Column(DateTime, nullable=True)
    stats_period_start = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    config = relationship("RepostConfig", backref="stats", uselist=False)
    
    def __repr__(self):
        return f"<RepostStats(config_id={self.config_id}, total={self.total_reposts}, successful={self.successful_reposts})>"
