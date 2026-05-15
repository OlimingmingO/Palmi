"""Enterprise WeChat callback API endpoints.

Handles:
- GET /api/wechat/callback — URL verification (WeCom admin validation)
- POST /api/wechat/callback — Receive messages, respond async
"""
import logging

from fastapi import APIRouter, Request, Response, Query, BackgroundTasks

from app.config import settings
from app.gateway.wecom_crypto import WXBizMsgCrypt, WeComCryptoError
from app.gateway.wecom_callback import parse_callback_message, extract_encrypt_from_body
from app.gateway.wecom_api import send_text_message
from app.services.dialogue import get_reply

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
    """Background task: get LLM reply and send via WeCom API.

    Args:
        user_id: WeCom user ID (FromUserName)
        content: User's text message
    """
    try:
        # For Phase 0, use user_id as elder_id directly (no DB lookup yet in background)
        reply = await get_reply(elder_id=user_id, user_message=content)

        # Send reply via WeCom API
        await send_text_message(user_id=user_id, content=reply)

    except Exception as e:
        logger.error("Failed to process reply for user %s: %s", user_id, str(e), exc_info=True)
