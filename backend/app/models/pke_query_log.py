"""PKE query log ORM model."""
import uuid

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class PkeQueryLog(Base):
    __tablename__ = "pke_query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id = Column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False)
    query_text = Column(Text, nullable=False, comment="User message that triggered the query")
    result_snippet = Column(Text, nullable=True, comment="First 200 chars of PKE response")
    hit = Column(Boolean, nullable=False, default=False, comment="Whether PKE returned non-empty result")
    latency_ms = Column(Integer, nullable=False, default=0, comment="Query duration in milliseconds")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_pke_query_logs_elder_created", "elder_id", "created_at"),
    )
