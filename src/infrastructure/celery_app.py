"""
Celery Configuration - Background Task Processing
"""
import os
from celery import Celery
from celery.schedules import crontab

# Redis URL for Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")

# Create Celery app
celery_app = Celery(
    "br_system",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "src.infrastructure.tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    
    # Results
    result_expires=86400,  # 24 hours
    
    # Queues
    task_default_queue="default",
    task_queues={
        "default": {},
        "ocr": {"routing_key": "ocr.#"},
        "llm": {"routing_key": "llm.#"},
        "reports": {"routing_key": "reports.#"},
    },
    
    # Rate limiting
    task_annotations={
        "src.infrastructure.tasks.process_ocr": {"rate_limit": "10/m"},
        "src.infrastructure.tasks.classify_expense": {"rate_limit": "30/m"},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        "generate-daily-reports": {
            "task": "src.infrastructure.tasks.generate_daily_reports",
            "schedule": crontab(hour=2, minute=0),  # 2:00 AM
        },
        "cleanup-old-files": {
            "task": "src.infrastructure.tasks.cleanup_old_files",
            "schedule": crontab(hour=3, minute=0),  # 3:00 AM
        },
        "recalculate-project-totals": {
            "task": "src.infrastructure.tasks.recalculate_all_projects",
            "schedule": crontab(hour=4, minute=0),  # 4:00 AM
        },
    }
)

# Task routing
celery_app.conf.task_routes = {
    "src.infrastructure.tasks.process_ocr": {"queue": "ocr"},
    "src.infrastructure.tasks.classify_expense": {"queue": "llm"},
    "src.infrastructure.tasks.generate_*": {"queue": "reports"},
}
