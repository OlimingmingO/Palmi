"""Conversation message ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class Conversation(Base):
    """A single message in a conversation with an elder."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("elders.id", ondelete="CASCADE"),
        nullable=False,
        comment="The elder this message belongs to",
    )
    role = Column(
        String(16),
        nullable=False,
        comment="Message role: user | assistant",
    )
    content = Column(Text, nullable=False, comment="Message text content")
    channel = Column(String(16), nullable=True)  # "wecom_kf", "ilink", "wecom_app"
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_conversations_elder_created", "elder_id", "created_at"),
    )

    def __repr__(self):
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<Conversation {self.role}: {preview}>"
