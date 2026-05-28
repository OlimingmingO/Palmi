"""Parse WeCom callback XML messages into structured data.

Extracted from Hermes Agent gateway/platforms/wecom_callback.py.
Only the message-parsing logic is kept — the HTTP server, adapter class,
access-token management, and agent integration are removed.  Our FastAPI
endpoint (``app.api.wechat``) calls these helpers directly.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET


def parse_callback_message(decrypted_xml: str) -> dict:
    """Parse a decrypted WeCom callback XML into a flat dict.

    Parameters
    ----------
    decrypted_xml:
        The inner XML string obtained after decrypting the ``<Encrypt>``
        payload (via :func:`wecom_crypto.decrypt_message`).

    Returns
    -------
    dict with keys:
        to_user     – receiving corp / app id (``<ToUserName>``)
        from_user   – sender's WeCom user id (``<FromUserName>``)
        create_time – message timestamp (int, unix epoch)
        msg_type    – "text", "image", "voice", "event", etc.
        content     – text body (empty string for non-text types)
        msg_id      – unique WeCom message id (may be empty for events)
        agent_id    – the agent/app that received the message
        event       – event name for msg_type=="event" (e.g. "subscribe")
        event_key   – event key payload (if any)
    """
    root = ET.fromstring(decrypted_xml)
    msg_type = (root.findtext("MsgType") or "").lower()

    return {
        "to_user": root.findtext("ToUserName", ""),
        "from_user": root.findtext("FromUserName", ""),
        "create_time": int(root.findtext("CreateTime", "0")),
        "msg_type": msg_type,
        "content": (root.findtext("Content") or "").strip(),
        "msg_id": root.findtext("MsgId", ""),
        "agent_id": root.findtext("AgentID", ""),
        # Event-specific fields (only populated for msg_type == "event")
        "event": (root.findtext("Event") or "").lower() if msg_type == "event" else "",
        "event_key": root.findtext("EventKey", "") if msg_type == "event" else "",
        # KF (Customer Service) event fields — present in kf_msg_or_event notifications
        "open_kf_id": root.findtext("OpenKfId", ""),
        "kf_token": root.findtext("Token", ""),
    }


def extract_encrypt_from_body(xml_body: str) -> str:
    """Extract the ``<Encrypt>`` value from a raw WeCom callback POST body.

    WeCom POSTs an outer XML envelope like::

        <xml>
            <ToUserName><![CDATA[corp_id]]></ToUserName>
            <Encrypt><![CDATA[...]]></Encrypt>
            <AgentID>1000002</AgentID>
        </xml>

    This helper extracts the ``Encrypt`` element so it can be passed to
    :func:`wecom_crypto.decrypt_message`.
    """
    root = ET.fromstring(xml_body)
    return root.findtext("Encrypt", default="")
