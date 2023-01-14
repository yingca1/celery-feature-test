import os
import time
from pathlib import Path
from celery import Celery, bootsteps
from celery.signals import import_modules,before_task_publish,after_task_publish,task_prerun,task_postrun,task_retry,task_success,task_failure,task_internal_error,task_received,task_revoked,task_unknown,task_rejected,celeryd_after_setup,celeryd_init,worker_init,worker_ready,heartbeat_sent,worker_shutting_down,worker_process_init,worker_process_shutdown,worker_shutdown,beat_init,beat_embedded_init
from celery.utils.log import get_task_logger
from billiard.process import current_process

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

HEARTBEAT_FILE = Path("./worker_heartbeat")
READINESS_FILE = Path("./worker_ready")


class BaseTask(celery.Task):
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        super().after_return(status, retval, task_id, args, kwargs, einfo)
        # celery.control.broadcast("shutdown", destination=[self.request.hostname])


@celery.task(name="blocking", base=BaseTask)
def blocking(secs: float):
    logger.info(f'[blocking] started')
    time.sleep(secs)
    logger.info(f'[blocking] finished')


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

celery.steps["worker"].add(LivenessProbe)

def kill_other_celery_process():
    p = current_process()
    logger.info(f"current process pid: {p.pid}")
    
    cmd = "ps auxww | grep 'celery' | "
    cmd += f"grep -v 'grep' | grep -v '{p.pid}' | "
    cmd += "awk '{print $2}' | "
    cmd += "xargs --no-run-if-empty kill -9"
    logger.info(f'[kill zombie processes] {cmd}')
    os.system(cmd)


@worker_ready.connect
def worker_ready_handler(**_):
    kill_other_celery_process()
    READINESS_FILE.touch()


@worker_shutdown.connect
def worker_shutdown_handler(**_):
    READINESS_FILE.unlink(missing_ok=True)
    kill_other_celery_process()


@task_postrun.connect(sender=blocking)
def postrun_handler(sender, **kwds):
    # print('@task_postrun', sender, kwds)
    print(sender.name)
    p = current_process()
    os.system(f"kill -15 {p.pid}")
    # celery.control.broadcast("shutdown", destination=[sender.request.hostname])
    # celery.control.revoke(sender.request.id, terminate=True)


# @worker_shutting_down.connect
# def worker_shutting_down_handler(sig, how, exitcode, ** kwargs):
#     print(f'worker_shutting_down({sig}, {how}, {exitcode})')
#     print(kwargs)
    # os.system("ps auxww | grep 'celery' | grep -v \" grep \" | awk '{print $2}' | xargs --no-run-if-empty kill -9")


# @celeryd_after_setup.connect
# def celeryd_after_setup_handler(**kwargs):
#     print(kwargs)
#     p = current_process()
#     print(f"current_process: {p}")
#     print(f"current_process: {p.pid}")
    
#     cmd = "ps auxww | grep 'celery' | "
#     cmd += f"grep -v 'grep' | grep -v '{p.pid}' | "
#     cmd += "awk '{print $2}' | "
#     cmd += "xargs --no-run-if-empty kill -9"
#     logger.info('run cmd kill zombie processes: \n')
#     logger.info(cmd)
#     os.system(cmd)


@before_task_publish.connect
@after_task_publish.connect
@task_prerun.connect
@task_postrun.connect
@task_retry.connect
@task_success.connect
@task_failure.connect
@task_internal_error.connect
@task_received.connect
@task_revoked.connect
@task_unknown.connect
@task_rejected.connect
# @celeryd_after_setup.connect
@celeryd_init.connect
@worker_init.connect
@worker_ready.connect
@worker_process_init.connect
@worker_process_shutdown.connect
@worker_shutting_down.connect
@worker_shutdown.connect
@import_modules.connect
# @heartbeat_sent.connect
@beat_init.connect
@beat_embedded_init.connect
def signal_handler(**kwargs):
    logger.debug(kwargs)
