"""
RepostLog model for tracking individual repost operations
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import Base, TimestampMixin


class RepostLog(Base, TimestampMixin):
    """Log of individual repost operations"""
    
    __tablename__ = "repost_logs"
    
    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey('repost_configs.id', ondelete='CASCADE'), nullable=False)
    
    source_message_id = Column(Integer, nullable=False)
    target_message_id = Column(Integer, nullable=True)  # Null if failed
    
    content_type = Column(String(50), nullable=False)  # 'text', 'photo', 'video', etc.
    status = Column(String(20), nullable=False)  # 'success', 'failed', 'filtered'
    error_message = Column(Text, nullable=True)
    
    reposted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    config = relationship("RepostConfig", backref="logs")
    
    def __repr__(self):
        return f"<RepostLog(config_id={self.config_id}, status={self.status}, content_type={self.content_type})>"
