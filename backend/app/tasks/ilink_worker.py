"""iLink Bot long-polling worker — persistent Celery task.

Continuously polls iLink getupdates API and routes incoming
text messages through the XiaoBan chat pipeline.

Start: Celery worker auto-discovers this task. Trigger manually via:
    from app.tasks.ilink_worker import ilink_poll_loop
    ilink_poll_loop.delay()
Or auto-start via Celery Beat if ILINK_ENABLED=true.
"""
import asyncio
import logging
import time

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

# Backoff settings for error recovery
_INITIAL_BACKOFF = 2  # seconds
_MAX_BACKOFF = 60  # seconds


@celery_app.task(bind=True, name="tasks.ilink_worker.ilink_poll_loop", max_retries=None)
def ilink_poll_loop(self):
    """Persistent long-polling worker for iLink messages.

    Runs an asyncio event loop internally. On transient errors,
    applies exponential backoff before retrying. Never exits
    unless ILINK_ENABLED is set to False.
    """
    if not settings.ILINK_ENABLED:
        logger.info("iLink is disabled (ILINK_ENABLED=False). Worker exiting.")
        return

    if not settings.ILINK_BOT_TOKEN:
        logger.warning("ILINK_BOT_TOKEN is empty. Worker exiting.")
        return

    logger.info("iLink polling worker started.")
    asyncio.run(_poll_loop())


async def _poll_loop():
    """Main async polling loop."""
    from app.gateway.ilink_bot import get_updates, save_context_token, send_typing
    from app.tasks.ilink_worker import _process_ilink_message

    cursor = ""
    backoff = _INITIAL_BACKOFF

    # Try to restore cursor from Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        saved_cursor = await r.get("ilink:poll_cursor")
        if saved_cursor:
            cursor = saved_cursor
            logger.info("Restored iLink poll cursor from Redis")
        await r.aclose()
    except Exception as e:
        logger.warning("Failed to restore iLink cursor: %s", e)

    while True:
        if not settings.ILINK_ENABLED:
            logger.info("iLink disabled mid-loop. Exiting.")
            break

        try:
            result = await get_updates(cursor=cursor)
            msgs = result.get("msgs", [])
            new_cursor = result.get("cursor", cursor)

            if new_cursor != cursor:
                cursor = new_cursor
                # Persist cursor to Redis
                try:
                    import redis.asyncio as aioredis
                    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                    await r.set("ilink:poll_cursor", cursor)
                    await r.aclose()
                except Exception:
                    pass

            for msg in msgs:
                try:
                    await _handle_message(msg)
                except Exception as e:
                    logger.error("Error handling iLink message: %s", e, exc_info=True)

            # Reset backoff on successful poll
            backoff = _INITIAL_BACKOFF

        except Exception as e:
            logger.error("iLink poll error: %s (backoff %ds)", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)


async def _handle_message(msg: dict):
    """Process a single inbound iLink message."""
    from app.gateway.ilink_bot import save_context_token, send_typing

    # Only process user-sent messages (message_type == 1)
    message_type = msg.get("message_type")
    if message_type != 1:
        return

    from_user_id = msg.get("from_user_id", "")
    context_token = msg.get("context_token", "")
    item_list = msg.get("item_list", [])

    if not from_user_id or not context_token:
        return

    # Save context_token for proactive messaging
    await save_context_token(from_user_id, context_token)

    # Extract text content
    text_content = ""
    for item in item_list:
        if item.get("type") == 1:
            text_content = item.get("text_item", {}).get("text", "").strip()
            break

    if not text_content:
        logger.debug("Non-text or empty iLink message from %s, skipping", from_user_id)
        return

    logger.info("iLink message from %s: %s", from_user_id, text_content[:50])

    # Send typing indicator (non-blocking)
    try:
        await send_typing(from_user_id, context_token)
    except Exception:
        pass

    # Process through the LLM pipeline
    await _process_ilink_message(from_user_id, text_content, context_token)


async def _process_ilink_message(ilink_user_id: str, content: str, context_token: str):
    """Process a message from iLink channel through the LLM pipeline.

    Same flow as _process_and_reply in wechat.py but uses iLink for reply.
    """
    import uuid

    from sqlalchemy import select

    from app.database import async_session_factory
    from app.gateway.ilink_bot import send_message
    from app.models.elder_profile import ElderProfile
    from app.pke.pke_service import pke_service
    from app.services import elder_service, conversation_service
    from app.services.dialogue import get_reply
    from app.tasks.conversation import store_conversation
    from app.tasks.memory import capture_conversation

    try:
        async with async_session_factory() as session:
            async with session.begin():
                # 1. Resolve or create elder (using iLink user_id as wechat_user_id)
                elder = await elder_service.get_or_create_elder(
                    db=session, wechat_user_id=ilink_user_id
                )
                elder_id = str(elder.id)

                # 1b. Load latest understanding profile
                profile_stmt = (
                    select(ElderProfile)
                    .where(ElderProfile.elder_id == elder.id)
                    .order_by(ElderProfile.version.desc())
                    .limit(1)
                )
                profile_result = await session.execute(profile_stmt)
                profile_obj = profile_result.scalar_one_or_none()
                profile_context = profile_obj.content if profile_obj else ""

                # 2. Load conversation history from DB
                history = await conversation_service.get_recent(
                    db=session, elder_id=elder.id, limit=10
                )

                # 3. Query PKE memory (fail-open)
                memory_ctx = await pke_service.query(elder_id, content)

                # 4. Get LLM reply
                reply = await get_reply(
                    elder_id=elder_id,
                    user_message=content,
                    history=history,
                    memory_context=memory_ctx,
                    profile_context=profile_context,
                )

                # 5. Pre-generate user message UUID for downstream tagging.
                user_msg_id = str(uuid.uuid4())

        # 5b. Dispatch durable persistence to Celery (outside DB transaction).
        store_conversation.delay(
            str(elder.id), "user", content, "ilink", user_msg_id
        )
        store_conversation.delay(
            str(elder.id), "assistant", reply, "ilink"
        )

        # 6. Async PKE capture
        try:
            capture_conversation.delay(elder_id, content, reply)
        except Exception as e:
            logger.warning("Failed to queue PKE capture: %s", e)

        # 6b. Intent tagging
        try:
            from app.tasks.tags import classify_tags
            classify_tags.delay(str(elder.id), user_msg_id)
        except Exception as _tag_err:
            logger.warning("Failed to queue intent classification: %s", _tag_err)

        # 7. Send reply via iLink
        await send_message(ilink_user_id, reply, context_token)

    except Exception as e:
        logger.error(
            "Failed to process iLink message for %s: %s",
            ilink_user_id, str(e), exc_info=True
        )
