"""Celery task for durable conversation persistence."""
import asyncio
import logging
import uuid

from app.celery_app import celery_app
from app.database import async_session_factory
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.conversation.store",
    queue="default",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=10,
)
def store_conversation(
    self,
    elder_id: str,
    role: str,
    content: str,
    channel: str = None,
    message_id: str = None,
):
    """Persist conversation turn to PostgreSQL with robust retry (max 10 attempts).

    Args:
        elder_id: UUID string of the elder
        role: 'user' or 'assistant'
        content: Message text content
        channel: Source channel (e.g. 'wecom_kf', 'ilink', 'wecom_app')
        message_id: Optional pre-generated UUID string for the message. When the
            caller needs to reference the message id synchronously (e.g. to
            dispatch follow-up tasks like intent classification), it should
            pre-generate the UUID and pass it here. If omitted, a fresh UUID is
            generated inside the task.

    Returns:
        The persisted message UUID as a string.
    """

    async def _persist():
        async with async_session_factory() as session:
            msg = Conversation(
                id=uuid.UUID(message_id) if message_id else uuid.uuid4(),
                elder_id=uuid.UUID(elder_id),
                role=role,
                content=content,
                channel=channel,
            )
            session.add(msg)
            await session.commit()
            logger.info("Persisted message %s for elder %s", msg.id, elder_id)
            return str(msg.id)

    return asyncio.run(_persist())
