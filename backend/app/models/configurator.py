"""Configurator account ORM model."""
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class Configurator(Base):
    __tablename__ = "configurators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id = Column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False)
    login_name = Column(String(128), unique=True, nullable=False, comment="Login identifier (email or username)")
    nickname = Column(String(64), nullable=True, comment="Display name")
    relationship = Column(String(32), nullable=False, comment="子女/社工/邻居/老伴/本人")
    phone = Column(String(20), nullable=True, comment="Phone for emergency SMS fallback")
    is_primary = Column(Boolean, nullable=False, default=False, comment="Primary contact for notifications")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_configurators_elder", "elder_id"),
    )
