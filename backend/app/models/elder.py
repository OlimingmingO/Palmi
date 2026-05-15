"""Elder user ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class Elder(Base):
    """Elder user — one record per elderly person being served."""

    __tablename__ = "elders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wechat_user_id = Column(String(128), unique=True, nullable=False, index=True, comment="Enterprise WeChat external_userid")
    nickname = Column(String(64), nullable=True, comment="Display name (e.g., '美兰阿姨')")
    phone = Column(String(20), nullable=True, comment="Phone number for voice calls")
    status = Column(String(16), nullable=False, default="active", comment="active / paused / archived")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'archived')", name="ck_elders_status"),
    )

    def __repr__(self):
        return f"<Elder {self.nickname or self.wechat_user_id} ({self.status})>"
