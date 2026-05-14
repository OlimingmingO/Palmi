"""tasks.trigger.* — Proactive reach tasks."""
from app.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.trigger.evaluate", queue="high_priority", max_retries=3)
def evaluate_triggers(self, elder_id: str):
    """Evaluate all trigger conditions for an elder."""
    # TODO: Check 7 trigger types, fire if conditions met
    pass


@celery_app.task(bind=True, name="tasks.trigger.send", queue="high_priority", max_retries=5)
def send_proactive_message(self, elder_id: str, trigger_type: str, content: str):
    """Deliver proactive message to elder via WeChat."""
    # TODO: Send through gateway/wecom.py
    pass
