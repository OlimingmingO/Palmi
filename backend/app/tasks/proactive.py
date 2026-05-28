"""Proactive outreach tasks — daily greetings and check-ins.

Task naming: tasks.proactive.*
Queue: default

The "cat-like presence" — 小伴 reaches out once a day like a friendly cat
that comes to check on you. Not pushy, not scheduled-feeling.
"""
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.proactive.send_morning_greeting")
def send_morning_greeting():
    """Send personalized morning greeting to all active elders.

    Triggered daily at 08:00 by Celery Beat.
    For each active elder:
    1. Query PKE for recent memory context
    2. Generate natural greeting via LLM
    3. Send via WeCom API
    """
    import asyncio
    asyncio.run(_send_greetings())


async def _send_greetings():
    """Async implementation of morning greeting dispatch."""
    from app.database import async_session_factory
    from app.models.elder import Elder
    from app.models.trigger import TriggerState
    from app.services.dialogue import generate_greeting
    from app.gateway.wecom_api import send_text_message
    from app.pke.pke_service import pke_service
    from sqlalchemy import select
    from datetime import date, datetime, timezone

    async with async_session_factory() as session:
        stmt = select(Elder).where(Elder.status == "active")
        result = await session.execute(stmt)
        elders = result.scalars().all()

    logger.info("Sending morning greetings to %d active elders", len(elders))

    for elder in elders:
        try:
            # Get memory context for personalized greeting
            memory_ctx = await pke_service.query(str(elder.id), "最近聊了什么")

            # Generate greeting with persona + memory
            greeting = await generate_greeting(str(elder.id), memory_ctx)

            # Send via WeCom
            await send_text_message(user_id=elder.wechat_user_id, content=greeting)
            logger.debug("Sent greeting to elder %s", elder.id)

            # Increment daily trigger count (morning greeting counts toward quota)
            async with async_session_factory() as session:
                stmt = select(TriggerState).where(TriggerState.elder_id == elder.id)
                result = await session.execute(stmt)
                state = result.scalar_one_or_none()
                today = date.today()
                if state is None:
                    state = TriggerState(
                        elder_id=elder.id,
                        today_trigger_count=1,
                        last_trigger_at=datetime.now(tz=timezone.utc),
                        today_date=today,
                    )
                    session.add(state)
                else:
                    if state.today_date != today:
                        state.today_trigger_count = 0
                        state.today_date = today
                    state.today_trigger_count += 1
                    state.last_trigger_at = datetime.now(tz=timezone.utc)
                await session.commit()

        except Exception as e:
            logger.error("Failed to greet elder %s: %s", elder.id, e)
            continue
