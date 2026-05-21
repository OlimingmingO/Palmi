"""TriggerLog and TriggerState ORM models — Phase 2 proactive trigger tracking."""
import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, Text, Integer, Boolean, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models import Base


class TriggerLog(Base):
    """One record per proactive message trigger event (sent or skipped)."""
    __tablename__ = "trigger_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    elder_id = Column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_type = Column(String(32), nullable=False, comment="weather / festival / memory / time_gap")
    reason = Column(Text, nullable=True, comment="Human-readable reason the trigger fired")
    message_content = Column(Text, nullable=True, comment="The message that was sent")
    message_id = Column(String(128), nullable=True, comment="WeCom API message_id from send response")
    status = Column(String(16), nullable=False, default="sent", comment="sent / skipped / failed")
    skip_reason = Column(Text, nullable=True, comment="Why the trigger was skipped")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('sent', 'skipped', 'failed')", name="ck_trigger_logs_status"),
        CheckConstraint("trigger_type IN ('weather', 'festival', 'memory', 'time_gap')", name="ck_trigger_logs_type"),
    )

    def __repr__(self):
        return f"<TriggerLog elder={self.elder_id} type={self.trigger_type} status={self.status}>"


class TriggerState(Base):
    """Per-elder daily trigger state — tracks frequency for rate limiting."""
    __tablename__ = "trigger_state"

    elder_id = Column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), primary_key=True)
    today_trigger_count = Column(Integer, nullable=False, default=0)
    last_trigger_at = Column(DateTime(timezone=True), nullable=True)
    today_date = Column(Date, nullable=False, server_default=func.current_date())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TriggerState elder={self.elder_id} count={self.today_trigger_count} date={self.today_date}>"
