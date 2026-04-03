from __future__ import annotations

import logging
from datetime import UTC, datetime

from services.dq import get_market_dq_service
from common import record_worker_audit_event
from worker.celery_app import celery_app
from worker.tasks.base import BaseTask


logger = logging.getLogger("ptr.worker.dq")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_checked_at(value: str | None) -> datetime:
    """Parse checked_at timestamp with error handling."""
    try:
        if not value:
            return datetime.now(UTC).replace(microsecond=0)
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse checked_at value: {value}", exc_info=True)
        raise ValueError(f"Invalid checked_at format: {value}") from e


@celery_app.task(name="worker.dq.dispatch_market_dq_scan", bind=True, base=BaseTask)
def dispatch_market_dq_scan(self) -> dict[str, str]:
    checked_at = _utc_now_iso()
    async_result = run_market_dq_scan.apply_async(kwargs={"checked_at": checked_at})
    record_worker_audit_event(
        object_type="market_dq_scan",
        object_id=checked_at,
        action="dispatch",
        result="queued",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={"dispatched_task_id": async_result.id},
    )
    logger.info(
        "market dq scan dispatched",
        extra={"task_id": self.request.id},
    )
    return {
        "status": "queued",
        "checked_at": checked_at,
        "dispatched_task_id": async_result.id,
    }


@celery_app.task(name="worker.dq.run_market_dq_scan", bind=True, base=BaseTask)
def run_market_dq_scan(
    self,
    checked_at: str | None = None,
    market_limit: int | None = None,
) -> dict:
    service = get_market_dq_service()
    parsed_checked_at = _parse_checked_at(checked_at)
    result = service.evaluate_markets(
        checked_at=parsed_checked_at,
        market_limit=market_limit,
    )
    record_worker_audit_event(
        object_type="market_dq_scan",
        object_id=parsed_checked_at.isoformat(),
        action="execute",
        result="success",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={
            "selected_markets": result.get("selected_markets"),
            "created": result.get("created"),
            "pass": result.get("pass"),
            "warn": result.get("warn"),
            "fail": result.get("fail"),
            "alerts_emitted": result.get("alerts_emitted"),
        },
    )
    for alert in result.get("alert_samples", []):
        logger.warning(
            "dq check emitted alert market=%s status=%s reasons=%s",
            alert.get("market_id"),
            alert.get("status"),
            ",".join(alert.get("blocking_reason_codes", [])) or "-",
            extra={"task_id": self.request.id},
        )
    logger.info(
        "market dq scan completed",
        extra={"task_id": self.request.id},
    )
    return result
