"""
RepostConfig model for auto-repost functionality
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger, JSON, DateTime
from datetime import datetime, timezone
from typing import Optional, List

from .base import Base, TimestampMixin


class RepostConfig(Base, TimestampMixin):
    """Configuration for auto-reposting from a source channel"""
    
    __tablename__ = "repost_configs"
    
    id = Column(Integer, primary_key=True)
    
    # Source channel info
    source_channel_id = Column(BigInteger, nullable=False, unique=True)
    source_channel_title = Column(String(255), nullable=False)
    source_channel_username = Column(String(255), nullable=True)
    
    # Target channel info
    target_channel_id = Column(BigInteger, nullable=False)
    target_channel_title = Column(String(255), nullable=False)
    
    # Monitoring settings
    is_enabled = Column(Boolean, default=True, nullable=False)
    check_interval_seconds = Column(Integer, default=120, nullable=False)  # 2 minutes
    last_processed_message_id = Column(Integer, default=0, nullable=False)
    
    # Repost settings
    watermark_text = Column(Text, nullable=True)
    repost_delay_seconds = Column(Integer, default=0, nullable=False)
    
    # Content filtering (JSON array of allowed types)
    allowed_content_types = Column(JSON, nullable=True)  # ['video', 'photo', etc.]
    
    # Status tracking
    status = Column(String(20), default='active', nullable=False)
    last_error = Column(Text, nullable=True)
    last_check_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<RepostConfig(source={self.source_channel_title}, target={self.target_channel_title}, enabled={self.is_enabled})>"
