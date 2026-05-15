"""Hermes Agent fork — messaging gateway layer.

Reused from Hermes Agent (github.com/OlimingmingO/hermes-agent):
- wecom_crypto.py : AES-CBC encryption / decryption for WeCom callbacks
- wecom_callback.py: Parse decrypted callback XML into structured dicts
- wecom_ws.py     : WebSocket gateway reference copy (not adapted yet)
- wecom.py        : Convenience re-exports from crypto + callback modules
- session.py      : Multi-tenant session management (Palmi-specific)
"""
