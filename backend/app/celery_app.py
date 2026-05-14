"""Celery application configuration with task routing."""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "palmi",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_concurrency=4,
    task_routes={
        "tasks.conversation.*": {"queue": "default"},
        "tasks.memory.*": {"queue": "default"},
        "tasks.trigger.*": {"queue": "high_priority"},
        "tasks.tags.*": {"queue": "default"},
        "tasks.unmet.*": {"queue": "low_priority"},
        "tasks.configurator.*": {"queue": "default"},
        "tasks.alert.*": {"queue": "high_priority"},
    },
    task_default_queue="default",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"])
