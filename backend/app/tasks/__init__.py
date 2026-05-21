"""Celery task definitions.

Task naming convention: tasks.{domain}.{action}
Routing: see app/celery_app.py for queue assignments

Domains:
- conversation: Message storage and processing
- memory: PKE capture and compile
- trigger: Proactive reach evaluation and delivery
- tags: Intent classification
- proactive: Morning greeting
- unmet: Unmet needs detection
- configurator: Leave-message transformation
- alert: Emergency notifications
"""
from app.tasks import conversation, memory, trigger, tags, proactive, unmet, configurator, alert  # noqa: F401
