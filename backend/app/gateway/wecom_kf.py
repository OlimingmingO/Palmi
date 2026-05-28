"""WeChat Customer Service (微信客服) API client.

Handles:
- Syncing messages from KF accounts (pull model)
- Sending replies to customers via KF
- Generating contact entry links (QR/URL)

These APIs use a separate access token obtained with WECOM_KF_SECRET.
"""
import logging
from typing import Optional

import httpx

from app.gateway.wecom_api import get_kf_access_token

logger = logging.getLogger(__name__)

BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/kf"


async def sync_kf_messages(
    cursor: str = "",
    open_kf_id: str = "",
    token: str = "",
    limit: int = 1000,
) -> dict:
    """Pull messages from a KF account using cursor-based pagination.

    Args:
        cursor: Pagination cursor from previous call (empty for first call)
        open_kf_id: The KF account ID (open_kfid from callback event)
        token: Token from the kf_msg_or_event notification
        limit: Max messages per request (default 1000, max 1000)

    Returns:
        dict with keys: msg_list (list), has_more (bool), next_cursor (str)
    """
    access_token = await get_kf_access_token()

    body = {"limit": limit}
    if cursor:
        body["cursor"] = cursor
    if open_kf_id:
        body["open_kfid"] = open_kf_id
    if token:
        body["token"] = token

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{BASE_URL}/sync_msg?access_token={access_token}",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("errcode", 0) != 0:
            logger.error("KF sync_msg failed: %s", data.get("errmsg", "unknown"))
            return {"msg_list": [], "has_more": False, "next_cursor": ""}

        return {
            "msg_list": data.get("msg_list", []),
            "has_more": bool(data.get("has_more", 0)),
            "next_cursor": data.get("next_cursor", ""),
        }


async def send_kf_message(
    open_kf_id: str,
    external_userid: str,
    content: str,
) -> dict:
    """Send a text message to a customer via KF account.

    Args:
        open_kf_id: The KF account ID
        external_userid: The customer's external_userid
        content: Text message content

    Returns:
        WeCom API response dict
    """
    access_token = await get_kf_access_token()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{BASE_URL}/send_msg?access_token={access_token}",
            json={
                "touser": external_userid,
                "open_kfid": open_kf_id,
                "msgtype": "text",
                "text": {"content": content},
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("errcode", 0) != 0:
            logger.error(
                "KF send_msg failed for %s: %s",
                external_userid,
                data.get("errmsg", "unknown"),
            )
        else:
            logger.info(
                "KF message sent to %s via %s (%d chars)",
                external_userid,
                open_kf_id,
                len(content),
            )

        return data


async def get_kf_contact_way(
    open_kf_id: str,
    scene: str = "1",
) -> dict:
    """Generate a contact entry link/QR for a KF account.

    Args:
        open_kf_id: The KF account ID
        scene: Scene value (default "1" for QR code scenario)

    Returns:
        dict with keys: url (str), qr_code (str — image URL of QR code)
    """
    access_token = await get_kf_access_token()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{BASE_URL}/add_contact_way?access_token={access_token}",
            json={
                "open_kfid": open_kf_id,
                "scene": scene,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("errcode", 0) != 0:
            logger.error("KF add_contact_way failed: %s", data.get("errmsg", "unknown"))
            return {"url": "", "qr_code": ""}

        return {
            "url": data.get("url", ""),
            "qr_code": data.get("qr_code", ""),
        }
