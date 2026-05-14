"""Multi-tenant session management.

Based on Hermes Agent Gateway Session, restructured for multi-tenant:
- session_key = f"{platform}:{elder_id}"
- One active session per elder per platform
- Concurrent session locking via Redis SETNX
- Session context includes: conversation history, active triggers, user state
"""
