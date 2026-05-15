"""Enterprise WeChat gateway — module index.

Concrete implementations live in sibling modules:

- ``wecom_crypto``    – AES-CBC encryption / decryption (callback mode)
- ``wecom_callback``  – Parse decrypted callback XML into structured dicts
- ``wecom_ws``        – WebSocket long-connection adapter (Phase 1 reference copy)
- ``session``         – Multi-tenant session management

This file re-exports the most commonly used helpers so callers can do::

    from app.gateway.wecom import decrypt_message, parse_callback_message
"""

from app.gateway.wecom_crypto import (  # noqa: F401
    WXBizMsgCrypt,
    WeComCryptoError,
    decrypt_message,
    encrypt_message,
    verify_signature,
)
from app.gateway.wecom_callback import (  # noqa: F401
    extract_encrypt_from_body,
    parse_callback_message,
)
