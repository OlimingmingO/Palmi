"""PKE memory tasks — async capture and daily compile.

Task naming: tasks.memory.*
Queue: default
"""
import logging

from app.celery_app import celery_app
from app.pke.pke_service import pke_service

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.memory.capture_conversation", bind=True, max_retries=2)
def capture_conversation(self, elder_id: str, user_msg: str, bot_reply: str):
    """Capture a conversation exchange to the elder's PKE vault.

    Called asynchronously after each dialogue turn.
    """
    try:
        pke_service.capture(elder_id, user_msg, bot_reply)
    except Exception as e:
        logger.error("Capture task failed for %s: %s", elder_id, e)
        raise self.retry(exc=e, countdown=30)


@celery_app.task(name="tasks.memory.compile_daily", bind=True)
def compile_daily(self, elder_id: str):
    """Run daily knowledge compilation for a single elder."""
    try:
        pke_service.compile_daily(elder_id)
    except Exception as e:
        logger.error("Daily compile failed for %s: %s", elder_id, e)


@celery_app.task(name="tasks.memory.compile_all_elders")
def compile_all_elders():
    """Run daily compile for ALL active elders.

    Triggered by Celery Beat at 03:00 daily.
    """
    from app.database import sync_session_factory
    from app.models.elder import Elder
    from sqlalchemy import select

    with sync_session_factory() as session:
        stmt = select(Elder).where(Elder.status == "active")
        elders = session.execute(stmt).scalars().all()

    logger.info("Starting daily compile for %d active elders", len(elders))

    for elder in elders:
        try:
            compile_daily.delay(str(elder.id))
        except Exception as e:
            logger.error("Failed to queue compile for %s: %s", elder.id, e)
