"""Enterprise WeChat callback API endpoints.

Handles:
- GET /api/wechat/callback — URL verification (WeCom admin validation)
- POST /api/wechat/callback — Receive messages, respond async
"""
import logging
import uuid

from fastapi import APIRouter, Request, Response, Query, BackgroundTasks

from app.config import settings
from app.database import async_session_factory
from app.gateway.wecom_crypto import WXBizMsgCrypt, WeComCryptoError
from app.gateway.wecom_callback import parse_callback_message, extract_encrypt_from_body
from app.gateway.wecom_api import send_text_message
from app.gateway.wecom_kf import sync_kf_messages, send_kf_message
from app.services import elder_service, conversation_service
from app.services.dialogue import get_reply
from app.pke.pke_service import pke_service
from app.tasks.conversation import store_conversation
from app.tasks.memory import capture_conversation
from app.models.elder_profile import ElderProfile
from sqlalchemy import select
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_crypto() -> WXBizMsgCrypt:
    """Create a WXBizMsgCrypt instance from settings."""
    token = settings.WECOM_TOKEN or settings.WECOM_SECRET
    encoding_aes_key = settings.WECOM_ENCODING_AES_KEY
    return WXBizMsgCrypt(
        token=token,
        encoding_aes_key=encoding_aes_key,
        receive_id=settings.WECOM_CORP_ID,
    )


@router.get("/callback")
async def verify_url(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """WeCom URL verification — decrypt echostr and return plaintext.

    WeCom sends this GET request when configuring the callback URL.
    We must decrypt echostr and return the plaintext to prove we own the endpoint.
    """
    try:
        crypto = _get_crypto()
        decrypted = crypto.verify_url(msg_signature, timestamp, nonce, echostr)
        return Response(content=decrypted, media_type="text/plain")
    except WeComCryptoError as e:
        logger.error("URL verification failed: %s", str(e))
        return Response(content="verification failed", status_code=403)
    except Exception as e:
        logger.error("URL verification error: %s", str(e), exc_info=True)
        return Response(content="error", status_code=500)


@router.post("/callback")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    """Receive WeCom message callback.

    Flow:
    1. Decrypt incoming XML
    2. Parse message
    3. Return 200 immediately (WeCom 5-second timeout)
    4. Process LLM + send reply in background
    """
    try:
        # Read raw body
        body = await request.body()
        body_str = body.decode("utf-8")

        # Extract encrypted content from XML body
        encrypt_str = extract_encrypt_from_body(body_str)
        if not encrypt_str:
            logger.warning("No <Encrypt> element found in callback body")
            return Response(content="", status_code=200)

        # Decrypt using the extracted encrypt string
        crypto = _get_crypto()
        decrypted_bytes = crypto.decrypt(msg_signature, timestamp, nonce, encrypt_str)
        decrypted_xml = decrypted_bytes.decode("utf-8")

        # Parse message
        msg = parse_callback_message(decrypted_xml)
        logger.info("Received message from %s: type=%s", msg.get("from_user"), msg.get("msg_type"))

        # Handle KF (Customer Service) event notifications
        if msg.get("msg_type") == "event" and msg.get("event") == "kf_msg_or_event":
            open_kf_id = msg.get("open_kf_id", "")
            kf_token = msg.get("kf_token", "")
            background_tasks.add_task(_process_kf_event, open_kf_id, kf_token)
            return Response(content="", status_code=200)

        # Only handle text messages for Phase 0
        if msg.get("msg_type") != "text":
            logger.debug("Ignoring non-text message type: %s", msg.get("msg_type"))
            return Response(content="", status_code=200)

        # Schedule async reply (don't block the callback response)
        from_user = msg["from_user"]
        content = msg.get("content", "")

        if content:
            background_tasks.add_task(_process_and_reply, from_user, content)

        # Return immediately — WeCom requires response within 5 seconds
        return Response(content="", status_code=200)

    except WeComCryptoError as e:
        logger.error("Message decryption failed: %s", str(e))
        return Response(content="", status_code=200)
    except Exception as e:
        logger.error("Callback processing error: %s", str(e), exc_info=True)
        return Response(content="", status_code=200)


async def _process_and_reply(user_id: str, content: str):
    """Background task: resolve elder, query memory, get LLM reply, persist, and send.

    Phase 1 flow:
    1. Resolve WeCom user → elder record (auto-create if new)
    2. Load recent conversation history from DB
    3. Query PKE memory for relevant context
    4. Call LLM with persona + memory + history
    5. Persist both user message and reply to DB
    6. Async capture to PKE vault (Celery task)
    7. Send reply via WeCom API
    """
    try:
        async with async_session_factory() as session:
            async with session.begin():
                # 1. Resolve or create elder
                elder = await elder_service.get_or_create_elder(
                    db=session, wechat_user_id=user_id
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

                # 3. Query PKE memory (fail-open, won't block on error)
                memory_ctx = await pke_service.query(elder_id, content)

                # 4. Call LLM with persona + memory + history
                reply = await get_reply(
                    elder_id=elder_id,
                    user_message=content,
                    history=history,
                    memory_context=memory_ctx,
                    profile_context=profile_context,
                )

                # 5. Pre-generate user message UUID so we can dispatch the
                #    intent-tagging task without waiting on persistence.
                user_msg_id = str(uuid.uuid4())

        # 5b. Dispatch durable persistence to Celery (outside DB transaction).
        store_conversation.delay(
            str(elder.id), "user", content, "wecom_kf", user_msg_id
        )
        store_conversation.delay(
            str(elder.id), "assistant", reply, "wecom_kf"
        )

        # 6. Async capture to PKE vault
        try:
            capture_conversation.delay(elder_id, content, reply)
        except Exception as e:
            logger.warning("Failed to queue PKE capture: %s", e)

        # 6b. Fire intent-tagging task for user message
        try:
            from app.tasks.tags import classify_tags
            classify_tags.delay(str(elder.id), user_msg_id)
        except Exception as _tag_err:
            logger.warning("Failed to queue intent classification: %s", _tag_err)

        # 7. Send reply via WeCom API
        await send_text_message(user_id=user_id, content=reply)

    except Exception as e:
        logger.error(
            "Failed to process reply for user %s: %s", user_id, str(e), exc_info=True
        )


async def _process_kf_event(open_kf_id: str, token: str):
    """Background task: pull KF messages and process each customer text message.

    Uses cursor-based pagination stored in Redis to avoid duplicate processing.
    """
    try:
        # Get cursor from Redis
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        cursor_key = f"kf:cursor:{open_kf_id}"
        cursor = await redis.get(cursor_key) or ""

        while True:
            result = await sync_kf_messages(
                cursor=cursor,
                open_kf_id=open_kf_id,
                token=token,
            )
            msg_list = result.get("msg_list", [])
            next_cursor = result.get("next_cursor", "")
            has_more = result.get("has_more", False)

            for kf_msg in msg_list:
                # Only process text messages from customers (origin=3)
                if kf_msg.get("origin") != 3:
                    continue
                if kf_msg.get("msgtype") != "text":
                    continue

                external_userid = kf_msg.get("external_userid", "")
                content = kf_msg.get("text", {}).get("content", "").strip()

                if not external_userid or not content:
                    continue

                # Process through the same LLM pipeline
                await _process_kf_message(open_kf_id, external_userid, content)

            # Save cursor for next time
            if next_cursor:
                await redis.set(cursor_key, next_cursor)
                cursor = next_cursor

            if not has_more:
                break

        await redis.aclose()

    except Exception as e:
        logger.error("KF event processing failed for %s: %s", open_kf_id, str(e), exc_info=True)


async def _process_kf_message(open_kf_id: str, external_userid: str, content: str):
    """Process a single KF customer message through the LLM pipeline and reply."""
    try:
        async with async_session_factory() as session:
            async with session.begin():
                # 1. Resolve or create elder
                elder = await elder_service.get_or_create_elder(
                    db=session, wechat_user_id=external_userid
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

                # 2. Load conversation history
                history = await conversation_service.get_recent(
                    db=session, elder_id=elder.id, limit=10
                )

                # 3. Query PKE memory
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
            str(elder.id), "user", content, "wecom_kf", user_msg_id
        )
        store_conversation.delay(
            str(elder.id), "assistant", reply, "wecom_kf"
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

        # 7. Reply via KF API (not internal message API)
        await send_kf_message(open_kf_id, external_userid, reply)

    except Exception as e:
        logger.error(
            "Failed to process KF message for user %s: %s",
            external_userid, str(e), exc_info=True
        )
