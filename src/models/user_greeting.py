"""
User greeting tracking model
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, BigInteger, Date, Boolean
from sqlalchemy.sql import func

from .base import Base, TimestampMixin


class UserGreeting(Base, TimestampMixin):
    """Model for tracking daily user greetings"""
    
    __tablename__ = "user_greetings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(Integer, nullable=False, index=True)
    greeting_date = Column(Date, nullable=False, default=func.current_date(), index=True)
    has_greeted = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<UserGreeting(user_id={self.user_id}, channel_id={self.channel_id}, date={self.greeting_date})>"