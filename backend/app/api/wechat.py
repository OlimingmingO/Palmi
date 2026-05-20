"""Enterprise WeChat callback API endpoints.

Handles:
- GET /api/wechat/callback — URL verification (WeCom admin validation)
- POST /api/wechat/callback — Receive messages, respond async
"""
import logging

from fastapi import APIRouter, Request, Response, Query, BackgroundTasks

from app.config import settings
from app.database import async_session_factory
from app.gateway.wecom_crypto import WXBizMsgCrypt, WeComCryptoError
from app.gateway.wecom_callback import parse_callback_message, extract_encrypt_from_body
from app.gateway.wecom_api import send_text_message
from app.services import elder_service, conversation_service
from app.services.dialogue import get_reply
from app.pke.pke_service import pke_service
from app.tasks.memory import capture_conversation

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
                )

                # 5. Persist new exchange to DB
                await conversation_service.save_message(
                    db=session, elder_id=elder.id, role="user", content=content
                )
                await conversation_service.save_message(
                    db=session, elder_id=elder.id, role="assistant", content=reply
                )

        # 6. Async capture to PKE vault (outside DB transaction)
        try:
            capture_conversation.delay(elder_id, content, reply)
        except Exception as e:
            logger.warning("Failed to queue PKE capture: %s", e)

        # 7. Send reply via WeCom API
        await send_text_message(user_id=user_id, content=reply)

    except Exception as e:
        logger.error(
            "Failed to process reply for user %s: %s", user_id, str(e), exc_info=True
        )
