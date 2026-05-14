"""Enterprise WeChat WebSocket Gateway.

Forked from Hermes Agent gateway/platforms/wecom.py (65KB).
TODO: Copy from Hermes Agent fork and add multi-tenant routing.

Features (from Hermes):
- WebSocket long connection with auto-reconnect (backoff [2,5,10,30,60]s)
- 30-second heartbeat keepalive
- Message deduplication (DEDUP_MAX_SIZE=1000)
- Image/file/voice upload (512KB chunks)
- DM strategy management

Palmi additions:
- Multi-tenant routing: session_key = f"wecom:{elder_id}"
- Tenant resolution: external_userid → elders.wechat_user_id → elder_id
- Per-user PKE vault context loading
"""
