"""Cron Scheduler — forked from Hermes Agent.

TODO: Copy from Hermes Agent cron/scheduler.py (77KB) and extend:
- Add per-user job registration (user_id in job metadata)
- Add trigger_type field for proactive reach categorization
- Integrate with Redis lock backend for distributed safety

Features (from Hermes):
- File-lock-based scheduling
- 60-second tick interval
- Prompt injection scanning
- Job delivery to specified platform/channel
- Per-job toolset configuration
"""
