"""Trigger Engine — evaluates proactive message trigger conditions for each elder.

Phase 2: 4 trigger types evaluated in priority order:
  1. calendar — Chinese festivals and solar terms (highest specificity)
  2. weather  — notable weather conditions (rain, cold, heat)
  3. memory   — PKE follow-up items from conversations
  4. time_gap — fallback: elder has been silent for > 24 hours

Frequency control:
  - Max PROACTIVE_MAX_PER_DAY (default 2) proactive messages per elder per day
  - Minimum PROACTIVE_MIN_GAP_HOURS (default 8) hours between messages
  - Silence hours: PROACTIVE_SILENCE_START (21:00) to PROACTIVE_SILENCE_END (08:00)
  - Note: the morning greeting from proactive.py counts as a separate daily message
    and is NOT deducted from the trigger quota (triggers are supplementary)
"""
import logging
import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Default frequency control values (overridden by settings if available)
_MAX_PER_DAY = 2
_MIN_GAP_HOURS = 8
_SILENCE_START = 21   # 21:00
_SILENCE_END = 8      # 08:00


def _get_settings():
    """Lazy import to avoid circular imports."""
    from app.config import settings
    return settings


class TriggerEngine:
    """Evaluates all proactive trigger conditions and enforces frequency limits."""

    # ──────────────────────────────────────────────
    # Frequency control
    # ──────────────────────────────────────────────

    def _frequency_limits(self) -> tuple[int, int, int, int]:
        """Return (max_per_day, min_gap_hours, silence_start, silence_end) from settings."""
        s = _get_settings()
        return (
            getattr(s, 'PROACTIVE_MAX_PER_DAY', _MAX_PER_DAY),
            getattr(s, 'PROACTIVE_MIN_GAP_HOURS', _MIN_GAP_HOURS),
            getattr(s, 'PROACTIVE_SILENCE_START', _SILENCE_START),
            getattr(s, 'PROACTIVE_SILENCE_END', _SILENCE_END),
        )

    def _is_silence_hours(self) -> bool:
        """Return True if current time is within the configured silence window."""
        now = datetime.now()
        hour = now.hour
        _, _, silence_start, silence_end = self._frequency_limits()
        # Window wraps midnight: e.g., 21:00 – 08:00
        if silence_start > silence_end:
            return hour >= silence_start or hour < silence_end
        return silence_start <= hour < silence_end

    async def _get_or_create_state(self, db: AsyncSession, elder_id: str) -> "TriggerState":
        """Fetch TriggerState for an elder, creating it if it doesn't exist."""
        from app.models.trigger import TriggerState
        stmt = select(TriggerState).where(TriggerState.elder_id == uuid.UUID(elder_id))
        result = await db.execute(stmt)
        state = result.scalar_one_or_none()
        if state is None:
            state = TriggerState(
                elder_id=uuid.UUID(elder_id),
                today_trigger_count=0,
                last_trigger_at=None,
                today_date=date.today(),
            )
            db.add(state)
            await db.flush()
        return state

    async def reset_if_new_day(self, db: AsyncSession, elder_id: str) -> None:
        """Lazily reset today_trigger_count when the date has rolled over."""
        state = await self._get_or_create_state(db, elder_id)
        today = date.today()
        if state.today_date != today:
            state.today_trigger_count = 0
            state.today_date = today
            await db.flush()

    async def can_trigger(self, db: AsyncSession, elder_id: str) -> tuple[bool, str]:
        """Check whether a proactive trigger is allowed right now.

        Returns:
            (allowed: bool, skip_reason: str)
            skip_reason is empty if allowed is True.
        """
        max_per_day, min_gap_hours, _, _ = self._frequency_limits()

        # 1. Check silence hours
        if self._is_silence_hours():
            return False, "silence_hours"

        # 2. Lazy daily reset
        await self.reset_if_new_day(db, elder_id)

        state = await self._get_or_create_state(db, elder_id)

        # 3. Check daily quota
        if state.today_trigger_count >= max_per_day:
            return False, f"daily_limit_reached ({state.today_trigger_count}/{max_per_day})"

        # 4. Check minimum gap since last trigger
        if state.last_trigger_at is not None:
            now = datetime.now(tz=state.last_trigger_at.tzinfo or timezone.utc)
            gap = now - state.last_trigger_at
            if gap < timedelta(hours=min_gap_hours):
                hours_left = min_gap_hours - gap.total_seconds() / 3600
                return False, f"min_gap_not_met ({hours_left:.1f}h remaining)"

        return True, ""

    async def record_trigger(
        self,
        db: AsyncSession,
        elder_id: str,
        trigger_type: str,
        reason: str,
        status: str,
        message_content: Optional[str] = None,
        message_id: Optional[str] = None,
        skip_reason: Optional[str] = None,
    ) -> "TriggerLog":
        """Persist a TriggerLog record and update TriggerState if sent."""
        from app.models.trigger import TriggerLog, TriggerState

        log = TriggerLog(
            elder_id=uuid.UUID(elder_id),
            trigger_type=trigger_type,
            reason=reason,
            message_content=message_content,
            message_id=message_id,
            status=status,
            skip_reason=skip_reason,
        )
        db.add(log)

        if status == "sent":
            state = await self._get_or_create_state(db, elder_id)
            state.today_trigger_count += 1
            state.last_trigger_at = datetime.now(tz=timezone.utc)

        await db.flush()
        return log

    # ──────────────────────────────────────────────
    # Individual trigger evaluators
    # ──────────────────────────────────────────────

    async def evaluate_calendar(self) -> tuple[bool, str]:
        """Check for Chinese festivals and upcoming solar terms."""
        try:
            from app.services.calendar_service import should_trigger_calendar
            return should_trigger_calendar()
        except Exception as e:
            logger.warning("Calendar trigger evaluation failed: %s", e)
            return False, ""

    async def evaluate_weather(self) -> tuple[bool, str]:
        """Check for notable weather conditions at the configured location."""
        try:
            s = _get_settings()
            if not getattr(s, 'WEATHER_ENABLED', True):
                return False, ""
            lat = getattr(s, 'WEATHER_LAT', 31.23)
            lon = getattr(s, 'WEATHER_LON', 121.47)
            from app.services.weather import should_trigger_weather
            return await should_trigger_weather(lat, lon)
        except Exception as e:
            logger.warning("Weather trigger evaluation failed: %s", e)
            return False, ""

    async def evaluate_memory(self, elder_id: str) -> tuple[bool, str]:
        """Query PKE wiki for follow-up items from recent conversations."""
        try:
            from app.pke.pke_service import pke_service
            # Search for pending follow-ups or recent conversation topics
            result = await pke_service.query(elder_id, "待跟进 最近聊到")
            if result and result.strip() and len(result.strip()) > 20:
                return True, result.strip()
        except Exception as e:
            logger.warning("Memory trigger evaluation failed for elder %s: %s", elder_id, e)
        return False, ""

    async def evaluate_time_gap(self, db: AsyncSession, elder_id: str) -> tuple[bool, str]:
        """Check if the elder has been silent for more than 24 hours."""
        try:
            from app.models.conversation import Conversation
            stmt = (
                select(func.max(Conversation.created_at))
                .where(
                    Conversation.elder_id == uuid.UUID(elder_id),
                    Conversation.role == "user",
                )
            )
            result = await db.execute(stmt)
            last_msg_at = result.scalar_one_or_none()

            if last_msg_at is None:
                # Never messaged — trigger a warm introduction reach-out
                return True, "elder_never_messaged"

            now = datetime.now(tz=last_msg_at.tzinfo or timezone.utc)
            gap = now - last_msg_at
            if gap > timedelta(hours=24):
                hours = int(gap.total_seconds() / 3600)
                return True, f"elder_silent_{hours}h"

        except Exception as e:
            logger.warning("Time gap evaluation failed for elder %s: %s", elder_id, e)

        return False, ""

    # ──────────────────────────────────────────────
    # Master evaluator
    # ──────────────────────────────────────────────

    async def evaluate_all(
        self,
        db: AsyncSession,
        elder_id: str,
    ) -> Optional[tuple[str, str]]:
        """Run all trigger evaluators in priority order.

        Checks frequency gate first, then evaluates:
          1. calendar (most specific — festival/solar term)
          2. weather (environmental context)
          3. memory (PKE follow-up from conversations)
          4. time_gap (fallback — elder has been silent)

        Returns:
            (trigger_type, trigger_context) if a trigger fires, or None.
            trigger_context is a string that will be injected into the
            proactive message generation prompt.
        """
        # Frequency gate
        allowed, skip_reason = await self.can_trigger(db, elder_id)
        if not allowed:
            logger.debug("Elder %s: trigger skipped — %s", elder_id, skip_reason)
            return None

        # Evaluate in priority order — first match wins
        evaluators = [
            ("calendar", self.evaluate_calendar()),
            ("weather", self.evaluate_weather()),
        ]

        for trigger_type, coro in evaluators:
            try:
                fired, context = await coro
                if fired:
                    logger.info("Elder %s: %s trigger fired — %s", elder_id, trigger_type, context[:80])
                    return trigger_type, context
            except Exception as e:
                logger.warning("Trigger evaluator %s error: %s", trigger_type, e)

        # Memory trigger (needs elder_id)
        try:
            fired, context = await self.evaluate_memory(elder_id)
            if fired:
                logger.info("Elder %s: memory trigger fired", elder_id)
                return "memory", context
        except Exception as e:
            logger.warning("Memory trigger error for elder %s: %s", elder_id, e)

        # Time gap fallback
        try:
            fired, context = await self.evaluate_time_gap(db, elder_id)
            if fired:
                logger.info("Elder %s: time_gap trigger fired — %s", elder_id, context)
                return "time_gap", context
        except Exception as e:
            logger.warning("Time gap trigger error for elder %s: %s", elder_id, e)

        return None


# Module-level singleton
trigger_engine = TriggerEngine()
