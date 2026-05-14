"""Trigger Service — Proactive reach evaluation and execution.

Responsibilities:
- Evaluate 7 trigger types (environment, calendar, behavior, memory, time-gap, content, care)
- Frequency control (max 2 proactive messages/day per elder)
- Generate contextual proactive messages via LLM
- Deliver through Hermes cron scheduler
"""
