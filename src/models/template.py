"""
Template model for storing predefined responses
"""

from sqlalchemy import Boolean, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .comment import CommentCategory


class Template(Base, TimestampMixin):
    """Template model for predefined responses"""
    
    __tablename__ = "templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[CommentCategory] = mapped_column(
        SQLEnum(CommentCategory), 
        nullable=False
    )
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Higher priority = used first
    
    # Foreign keys
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id"), nullable=False)
    
    # Relationships
    channel = relationship("Channel", back_populates="templates")
    
    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name='{self.name}', category={self.category.value})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "template_text": self.template_text,
            "is_active": self.is_active,
            "priority": self.priority,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }