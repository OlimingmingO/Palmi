"""tasks.alert.* — Emergency notification tasks."""
from app.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.alert.send", queue="high_priority", max_retries=5)
def send_alert(self, elder_id: str, alert_level: str, summary: str):
    """Send emergency alert to linked configurators."""
    # TODO: Multi-channel notification (WeChat template + SMS)
    pass
