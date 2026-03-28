from __future__ import annotations

import logging
from datetime import datetime, timezone

from worker.celery_app import celery_app
from worker.config import settings
from worker.tasks.base import BaseTask


logger = logging.getLogger("ptr.worker.system")


@celery_app.task(name="worker.system.heartbeat", base=BaseTask, bind=True)
def emit_heartbeat(self: BaseTask) -> dict[str, str]:
    idempotency_key = self.make_idempotency_key("worker.system.heartbeat", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"))
    logger.info(
        "worker heartbeat emitted",
        extra={"task_id": self.request.id or idempotency_key},
    )
    return {
        "status": "ok",
        "task": "worker.system.heartbeat",
        "environment": settings.app_env,
        "rule_version": settings.rule_version,
        "idempotency_key": idempotency_key,
    }

