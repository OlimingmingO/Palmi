"""Elder profile (understanding document) ORM model."""
import uuid

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class ElderProfile(Base):
    __tablename__ = "elder_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id = Column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False, comment="Structured understanding doc (Markdown)")
    version = Column(Integer, nullable=False, default=1, comment="Version number, increments on update")
    last_updated_by = Column(String(16), nullable=False, default="configurator", comment="Source: configurator / system / elder")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_elder_profiles_elder_version", "elder_id", "version"),
    )
