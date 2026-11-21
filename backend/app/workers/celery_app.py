from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "opspilot",
    broker = settings.REDIS_URL,
    backend = settings.REDIS_URL,
    include = [
        "app.workers.docker_tasks"
    ]
)

celery_app.conf.update(
    task_track_started = True,
    task_serializer = "json",
    accept_content = ["json"],
    result_serializer = "json",
    timezone = "Asia/Kolkata",
    enable_utc = True
)