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


# KF Token cache (separate from app token — different secret)
_kf_access_token: Optional[str] = None
_kf_token_expires_at: float = 0


async def get_kf_access_token() -> str:
    """Get WeCom KF (Customer Service) access token, refreshing if expired.

    Uses WECOM_SECRET (KF API auth uses the bound app's secret).
    """
    global _kf_access_token, _kf_token_expires_at

    if _kf_access_token and time.time() < _kf_token_expires_at - 300:
        return _kf_access_token

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
            raise RuntimeError(f"WeCom KF token error: {data.get('errmsg', 'unknown')}")

        _kf_access_token = data["access_token"]
        _kf_token_expires_at = time.time() + data.get("expires_in", 7200)
        logger.info("WeCom KF access token refreshed, expires in %ds", data.get("expires_in", 7200))
        return _kf_access_token


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


async def get_user_name(user_id: str) -> Optional[str]:
    """Fetch the display name of a WeCom user by userid.

    Tries internal user API first, then external contact API as fallback.
    Returns None if both fail (non-fatal — used for best-effort nickname matching).
    """
    try:
        token = await get_access_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try internal user first
            resp = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/user/get",
                params={"access_token": token, "userid": user_id},
            )
            data = resp.json()
            if data.get("errcode", 0) == 0:
                return data.get("name")
            # Fallback: external contact
            resp2 = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get",
                params={"access_token": token, "external_userid": user_id},
            )
            data2 = resp2.json()
            if data2.get("errcode", 0) == 0:
                return data2.get("external_contact", {}).get("name")
    except Exception as exc:
        logger.warning("Failed to fetch WeCom user name for %s: %s", user_id, exc)
    return None
