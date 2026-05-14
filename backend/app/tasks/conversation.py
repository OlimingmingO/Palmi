"""tasks.conversation.* — Conversation storage tasks."""
from app.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="tasks.conversation.store",
    queue="default",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def store_conversation(self, elder_id: str, session_data: dict):
    """Persist conversation turn to PostgreSQL."""
    # TODO: Validate tenant, write to conversations + messages tables
    pass
