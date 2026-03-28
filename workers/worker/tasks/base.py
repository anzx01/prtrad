from __future__ import annotations

import logging
from hashlib import sha256
from typing import Any

from celery import Task


logger = logging.getLogger("ptr.worker.tasks")


class BaseTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True
    max_retries = 3

    def make_idempotency_key(self, *parts: Any) -> str:
        raw = "|".join(str(part) for part in parts)
        return sha256(raw.encode("utf-8")).hexdigest()

    def on_retry(self, exc: Exception, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any], einfo: Any) -> None:
        logger.warning(
            "task retry scheduled",
            extra={"task_id": task_id},
        )

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        logger.error(
            "task failed",
            extra={"task_id": task_id},
        )

