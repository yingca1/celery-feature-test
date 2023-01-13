import os
from celery import Celery

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get(
    "CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379")
celery.conf.result_expires = 60 * 60 * 24 * 30 * 12
celery.conf.mongodb_backend_settings = {
    'database': 'celery',
    'taskmeta_collection': 'celery_taskmeta',
}

@celery.task(name="blocking")
def blocking(secs: float):
    pass
