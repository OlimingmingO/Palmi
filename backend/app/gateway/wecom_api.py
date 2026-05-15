"""Enterprise WeChat REST API client.

Handles:
- Access token management (auto-refresh, cached)
- Sending text messages to users
"""
import logging
import time
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Token cache
_access_token: Optional[str] = None
_token_expires_at: float = 0


async def get_access_token() -> str:
    """Get WeCom access token, refreshing if expired.

    WeCom tokens are valid for 7200 seconds.
    We refresh 5 minutes early to avoid edge-case failures.
    """
    global _access_token, _token_expires_at

    if _access_token and time.time() < _token_expires_at - 300:
        return _access_token

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={
                "corpid": settings.WECOM_CORP_ID,
                "corpsecret": settings.WECOM_SECRET,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"WeCom token error: {data.get('errmsg', 'unknown')}")

        _access_token = data["access_token"]
        _token_expires_at = time.time() + data.get("expires_in", 7200)
        logger.info("WeCom access token refreshed, expires in %ds", data.get("expires_in", 7200))
        return _access_token


async def send_text_message(user_id: str, content: str) -> dict:
    """Send a text message to a WeCom user.

    Args:
        user_id: The WeCom user ID (external_userid or internal userid)
        content: Text message content

    Returns:
        WeCom API response dict
    """
    token = await get_access_token()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}",
            json={
                "touser": user_id,
                "msgtype": "text",
                "agentid": int(settings.WECOM_AGENT_ID) if settings.WECOM_AGENT_ID else 0,
                "text": {"content": content},
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("errcode", 0) != 0:
            logger.error("WeCom send failed: %s", data.get("errmsg", "unknown"))
        else:
            logger.info("Message sent to user %s (%d chars)", user_id, len(content))

        return data
