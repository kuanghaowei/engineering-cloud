"""Celery Application Configuration"""

from celery import Celery
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Create Celery application
celery_app = Celery(
    "aec_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[]  # Task modules will be added here
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

logger.info("Celery application configured")
