"""tasks.tags.* — Intent classification tasks."""
from app.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.tags.classify", queue="default", max_retries=3)
def classify_tags(self, elder_id: str, conversation_id: str):
    """LLM-based intent tag classification for a conversation."""
    # TODO: Call LLM to classify conversation intent
    pass
