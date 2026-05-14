"""Structured logging with PII redaction.

Rules:
- elder_id is loggable (tenant identifier)
- Conversation content MUST be redacted in logs
- Phone numbers MUST be masked (show last 4 digits only)
- Health information MUST NOT appear in logs
"""
