"""tasks.configurator.* — Configurator message processing tasks."""
from app.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.configurator.transform", queue="default", max_retries=3)
def transform_message(self, elder_id: str, raw_message: str, configurator_id: str):
    """Transform family message into natural conversational delivery."""
    # TODO: LLM transformation + delivery timing calculation
    pass
