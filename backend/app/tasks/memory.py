"""tasks.memory.* — PKE memory tasks."""
from app.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.memory.capture", queue="default", max_retries=3)
def capture_memory(self, elder_id: str, session_data: dict):
    """Capture conversation as evidence in user's raw/ vault."""
    # TODO: Call pke.capture with session data
    pass


@celery_app.task(bind=True, name="tasks.memory.compile", queue="default", max_retries=2)
def compile_memory(self, elder_id: str):
    """Compile recent raw/ evidence into wiki/ knowledge."""
    # TODO: Call pke.compile for the user
    pass
