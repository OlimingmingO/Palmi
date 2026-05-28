"""iLink Bot API client — Personal WeChat channel via Tencent iLink protocol.

Handles:
- Long-polling for incoming messages (getupdates)
- Sending text replies (sendmessage)
- Typing indicators (sendtyping)
- Context token persistence (Redis)

Protocol: HTTP/JSON at https://ilinkai.weixin.qq.com
Auth: Bearer token from QR login, random X-WECHAT-UIN per request.
"""
import base64
import logging
import random
import struct
from typing import Optional

import httpx
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# Redis key prefix for context tokens
_CTX_PREFIX = "ilink:ctx:"


def _build_headers() -> dict:
    """Build iLink API request headers.
    
    Each request requires:
    - Authorization: Bearer {bot_token}
    - AuthorizationType: ilink_bot_token
    - X-WECHAT-UIN: base64(str(random_uint32)) — anti-replay
    """
    uin_int = random.randint(0, 2**32 - 1)
    uin_b64 = base64.b64encode(str(uin_int).encode()).decode()
    return {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "Authorization": f"Bearer {settings.ILINK_BOT_TOKEN}",
        "X-WECHAT-UIN": uin_b64,
    }


async def get_updates(cursor: str = "") -> dict:
    """Long-poll for new messages from iLink.
    
    Holds connection for up to 35 seconds waiting for messages.
    
    Args:
        cursor: Pagination cursor from previous call (empty for first call).
        
    Returns:
        dict with keys:
        - msgs: list of message dicts
        - cursor: new cursor for next call
        - has_more: whether more messages are available
    """
    url = f"{settings.ILINK_BASE_URL}/ilink/bot/getupdates"
    body = {
        "get_updates_buf": cursor,
        "base_info": {"channel_version": "1.0.2"},
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            resp = await client.post(url, json=body, headers=_build_headers())
            resp.raise_for_status()
            data = resp.json()

            if data.get("ret", -1) != 0:
                logger.warning("iLink getupdates error: ret=%s", data.get("ret"))
                return {"msgs": [], "cursor": cursor, "has_more": False}

            return {
                "msgs": data.get("msgs", []),
                "cursor": data.get("get_updates_buf", cursor),
                "has_more": len(data.get("msgs", [])) > 0,
            }
        except httpx.TimeoutException:
            # Normal — long-poll timeout with no new messages
            return {"msgs": [], "cursor": cursor, "has_more": False}
        except Exception as e:
            logger.error("iLink getupdates failed: %s", e)
            return {"msgs": [], "cursor": cursor, "has_more": False}


async def send_message(to_user_id: str, text: str, context_token: str) -> dict:
    """Send a text message to a user via iLink.
    
    Args:
        to_user_id: Recipient user ID (format: xxx@im.wechat)
        text: Message text content
        context_token: Required token from inbound message (for reply association)
        
    Returns:
        API response dict
    """
    url = f"{settings.ILINK_BASE_URL}/ilink/bot/sendmessage"
    body = {
        "msg": {
            "to_user_id": to_user_id,
            "message_type": 2,  # Bot sending
            "message_state": 2,  # FINISH (complete message)
            "context_token": context_token,
            "item_list": [
                {"type": 1, "text_item": {"text": text}}
            ],
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=body, headers=_build_headers())
            resp.raise_for_status()
            data = resp.json()

            if data.get("ret", -1) != 0:
                logger.error(
                    "iLink sendmessage failed for %s: ret=%s",
                    to_user_id, data.get("ret"),
                )
            else:
                logger.info(
                    "iLink message sent to %s (%d chars)",
                    to_user_id, len(text),
                )
            return data
        except Exception as e:
            logger.error("iLink sendmessage error for %s: %s", to_user_id, e)
            return {"ret": -1, "error": str(e)}


async def send_typing(to_user_id: str, context_token: str) -> None:
    """Send typing indicator to a user.
    
    Non-critical — failures are silently logged.
    """
    url = f"{settings.ILINK_BASE_URL}/ilink/bot/sendtyping"
    body = {
        "msg": {
            "to_user_id": to_user_id,
            "context_token": context_token,
        }
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(url, json=body, headers=_build_headers())
            resp.raise_for_status()
        except Exception as e:
            logger.debug("iLink sendtyping failed: %s", e)


# ---- Context Token Persistence (Redis) ----

async def save_context_token(user_id: str, token: str) -> None:
    """Persist a user's context_token to Redis for proactive messaging.
    
    Tokens are stored indefinitely (no TTL) since we don't know their expiry.
    """
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.set(f"{_CTX_PREFIX}{user_id}", token)
        await r.aclose()
    except Exception as e:
        logger.warning("Failed to save context token for %s: %s", user_id, e)


async def get_context_token(user_id: str) -> Optional[str]:
    """Retrieve a stored context_token for proactive messaging.
    
    Returns None if no token is stored (user has never messaged us).
    """
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        token = await r.get(f"{_CTX_PREFIX}{user_id}")
        await r.aclose()
        return token
    except Exception as e:
        logger.warning("Failed to get context token for %s: %s", user_id, e)
        return None


# ---- QR Login Flow (for admin setup) ----

async def request_qr_code() -> dict:
    """Request a login QR code from iLink.
    
    Returns:
        dict with keys: qrcode (str), qrcode_img_content (str — base64 image or URL)
    """
    url = f"{settings.ILINK_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3"
    
    # QR request doesn't need bot_token auth
    headers = {
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return {
            "qrcode": data.get("qrcode", ""),
            "qrcode_img_content": data.get("qrcode_img_content", ""),
            "qrcode_img_url": data.get("qrcode_img_url", ""),
        }


async def check_qr_status(qrcode: str) -> dict:
    """Check QR code scan status.
    
    Returns:
        dict with keys:
        - status: "waiting" | "scanned" | "confirmed" | "expired"
        - bot_token: str (only when confirmed)
        - baseurl: str (only when confirmed)
        - account_id: str (only when confirmed)
    """
    url = f"{settings.ILINK_BASE_URL}/ilink/bot/get_qrcode_status?qrcode={qrcode}"
    
    headers = {
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            status = data.get("status", "waiting")
            result = {"status": status}
            
            if status == "confirmed":
                result["bot_token"] = data.get("bot_token", "")
                result["baseurl"] = data.get("baseurl", "")
                result["account_id"] = data.get("account_id", "")
            
            return result
        except httpx.TimeoutException:
            return {"status": "waiting"}
        except Exception as e:
            logger.error("iLink QR status check failed: %s", e)
            return {"status": "error", "detail": str(e)}
