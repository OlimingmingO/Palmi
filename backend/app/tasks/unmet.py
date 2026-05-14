"""tasks.unmet.* — Unmet needs detection tasks."""
from app.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.unmet.detect", queue="low_priority", max_retries=3)
def detect_unmet_need(self, elder_id: str, conversation_id: str):
    """Detect unmet needs from conversation content."""
    # TODO: LLM analysis for needs that couldn't be fulfilled
    pass
