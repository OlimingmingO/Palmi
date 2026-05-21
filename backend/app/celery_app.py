"""Celery application configuration with task routing."""
from celery import Celery
from celery.schedules import crontab

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
    beat_schedule={
        "morning-greeting": {
            "task": "tasks.proactive.send_morning_greeting",
            "schedule": crontab(hour=8, minute=0),
        },
        "daily-pke-compile": {
            "task": "tasks.memory.compile_all_elders",
            "schedule": crontab(hour=3, minute=0),
        },
        "trigger-evaluate": {
            "task": "tasks.trigger.evaluate_all_elders",
            "schedule": crontab(minute="*/15"),
        },
        "trigger-daily-reset": {
            "task": "tasks.trigger.reset_daily_trigger_counts",
            "schedule": crontab(hour=0, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
