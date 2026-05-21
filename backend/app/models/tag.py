"""IntentTag, MessageTag, TagCorrection ORM models — Phase 2 intent classification."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, SmallInteger, Boolean, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class IntentTag(Base):
    """Intent taxonomy — 9 predefined categories for conversation classification."""
    __tablename__ = "intent_tags"

    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(SmallInteger, nullable=False, default=0)

    def __repr__(self):
        return f"<IntentTag {self.name}>"


class MessageTag(Base):
    """Association between a conversation message and an intent tag."""
    __tablename__ = "message_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id = Column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(SmallInteger, ForeignKey("intent_tags.id"), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    source = Column(String(16), nullable=False, default="llm", comment="llm / manual")
    needs_review = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("source IN ('llm', 'manual')", name="ck_message_tags_source"),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_message_tags_confidence"),
    )

    def __repr__(self):
        return f"<MessageTag message={self.message_id} tag={self.tag_id} conf={self.confidence:.2f}>"


class TagCorrection(Base):
    """Manual correction record for a message tag (ops backend audit trail)."""
    __tablename__ = "tag_corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_tag_id = Column(UUID(as_uuid=True), ForeignKey("message_tags.id", ondelete="CASCADE"), nullable=False, index=True)
    original_tag_id = Column(SmallInteger, ForeignKey("intent_tags.id"), nullable=False)
    corrected_tag_id = Column(SmallInteger, ForeignKey("intent_tags.id"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<TagCorrection {self.original_tag_id} → {self.corrected_tag_id}>"
