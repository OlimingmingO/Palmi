"""Unmet need ORM model."""
import uuid

from sqlalchemy import Column, String, Text, Integer, Boolean, Float, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class UnmetNeed(Base):
    __tablename__ = "unmet_needs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id = Column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    need_description = Column(Text, nullable=False, comment="Extracted need description")
    need_category = Column(String(64), nullable=False, comment="Need category (e.g., 购物类, 打车类)")
    confidence = Column(Float, nullable=False, default=0.8, comment="Detection confidence 0.0-1.0")
    occurrence_count = Column(Integer, nullable=False, default=1, comment="Times this category appeared for this elder")
    is_dismissed = Column(Boolean, nullable=False, default=False, comment="Marked as false positive by ops")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_unmet_needs_elder_category", "elder_id", "need_category"),
        Index("idx_unmet_needs_dismissed", "is_dismissed"),
    )
