import os
import time
from pathlib import Path
from celery import Celery, bootsteps
from celery.signals import worker_ready, worker_shutdown
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

celery = Celery(__name__)
# https://docs.celeryq.dev/en/stable/userguide/workers.html#max-tasks-per-child-setting
# can avoid memory leaks, but only work with prefork pool
# celery.conf.worker_max_tasks_per_child = 1
celery.conf.worker_prefetch_multiplier = 1
celery.conf.task_acks_late = True
celery.conf.task_track_started = True
celery.conf.broker_pool_limit = 0
celery.conf.broker_heartbeat = 0
celery.conf.broker_connection_timeout = 10
celery.conf.broker_transport_options = { 'visibility_timeout': 60 * 60 * 3 }
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")
celery.conf.result_expires = 60 * 60 * 24 * 30
celery.conf.mongodb_backend_settings = {
    "database": "celery",
    "taskmeta_collection": "celery_taskmeta",
}

HEARTBEAT_FILE = Path("/tmp/worker_heartbeat")
READINESS_FILE = Path("/tmp/worker_ready")

class LivenessProbe(bootsteps.StartStopStep):
    requires = {'celery.worker.components:Timer'}

    def __init__(self, worker, **kwargs):
        self.requests = []
        self.tref = None

    def start(self, worker):
        self.tref = worker.timer.call_repeatedly(
            1.0, self.update_heartbeat_file, (worker,), priority=10,
        )

    def stop(self, worker):
       HEARTBEAT_FILE.unlink(missing_ok=True)

    def update_heartbeat_file(self, worker):
       HEARTBEAT_FILE.touch()


@worker_ready.connect
def worker_ready(**_):
   READINESS_FILE.touch()


@worker_shutdown.connect
def worker_shutdown(**_):
   READINESS_FILE.unlink(missing_ok=True)

celery.steps["worker"].add(LivenessProbe)

@celery.task(name="blocking")
def blocking(secs: float):
    logger.info(f'[blocking] started')
    time.sleep(secs)
    logger.info(f'[blocking] finished')
