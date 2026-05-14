"""Celery task definitions.

Task naming convention: tasks.{domain}.{action}
Routing: see app/celery_app.py for queue assignments

Domains:
- conversation: Message storage and processing
- memory: PKE capture and compile
- trigger: Proactive reach evaluation and delivery
- tags: Intent classification
- unmet: Unmet needs detection
- configurator: Leave-message transformation
- alert: Emergency notifications
"""
