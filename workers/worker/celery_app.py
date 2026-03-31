import logging
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from worker.config import settings
from worker.logging_utils import configure_logging

configure_logging()
logger = logging.getLogger("ptr.worker")

celery_app = Celery(
    "polymarket_tail_risk",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    imports=("worker.tasks.system", "worker.tasks.ingest", "worker.tasks.dq", "worker.tasks.tagging"),
    task_default_queue="default",
    worker_hijack_root_logger=False,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "system-heartbeat-every-minute": {
            "task": "worker.system.heartbeat",
            "schedule": crontab(minute="*/1"),
        },
        "dispatch-market-sync": {
            "task": "worker.ingest.dispatch_market_sync",
            "schedule": timedelta(seconds=settings.ingest_market_sync_interval_seconds),
        },
        "dispatch-snapshot-capture": {
            "task": "worker.ingest.dispatch_snapshot_capture",
            "schedule": timedelta(seconds=settings.ingest_snapshot_interval_seconds),
        },
        "dispatch-market-dq-scan": {
            "task": "worker.dq.dispatch_market_dq_scan",
            "schedule": timedelta(seconds=settings.dq_run_interval_seconds),
        },
        **(
            {
                "dispatch-market-auto-tagging": {
                    "task": "worker.tagging.dispatch_market_auto_classification",
                    "schedule": timedelta(seconds=settings.tagging_run_interval_seconds),
                }
            }
            if settings.tagging_run_interval_seconds > 0
            else {}
        ),
    },
    beat_scheduler="celery.beat.PersistentScheduler",
    beat_schedule_filename=settings.celery_beat_schedule_db,
)


@celery_app.task(name="worker.healthcheck")
def healthcheck() -> dict[str, str]:
    logger.info("worker healthcheck ok", extra={"task_id": "healthcheck"})
    return {
        "status": "ok",
        "service": "worker",
        "environment": settings.app_env,
        "rule_version": settings.rule_version,
    }
