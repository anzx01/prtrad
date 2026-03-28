from __future__ import annotations

import logging
from datetime import UTC, datetime

from services.ingest import get_polymarket_ingest_service
from worker.celery_app import celery_app
from worker.tasks.base import BaseTask


logger = logging.getLogger("ptr.worker.ingest")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_triggered_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC).replace(microsecond=0)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@celery_app.task(name="worker.ingest.dispatch_market_sync", bind=True, base=BaseTask)
def dispatch_market_sync(self) -> dict[str, str]:
    triggered_at = _utc_now_iso()
    async_result = run_market_catalog_sync.apply_async(kwargs={"triggered_at": triggered_at})
    logger.info(
        "market sync dispatched",
        extra={"task_id": self.request.id},
    )
    return {
        "status": "queued",
        "triggered_at": triggered_at,
        "dispatched_task_id": async_result.id,
    }


@celery_app.task(name="worker.ingest.run_market_catalog_sync", bind=True, base=BaseTask)
def run_market_catalog_sync(
    self,
    triggered_at: str | None = None,
    force_full_scan: bool = False,
    limit_pages: int | None = None,
) -> dict:
    service = get_polymarket_ingest_service()
    parsed_triggered_at = _parse_triggered_at(triggered_at)
    result = service.sync_markets(
        triggered_at=parsed_triggered_at,
        force_full_scan=force_full_scan,
        limit_pages=limit_pages,
    )
    logger.info(
        "market sync completed",
        extra={"task_id": self.request.id},
    )
    return result


@celery_app.task(name="worker.ingest.dispatch_snapshot_capture", bind=True, base=BaseTask)
def dispatch_snapshot_capture(self) -> dict[str, str]:
    triggered_at = _utc_now_iso()
    async_result = capture_active_market_snapshots.apply_async(kwargs={"triggered_at": triggered_at})
    logger.info(
        "snapshot capture dispatched",
        extra={"task_id": self.request.id},
    )
    return {
        "status": "queued",
        "triggered_at": triggered_at,
        "dispatched_task_id": async_result.id,
    }


@celery_app.task(name="worker.ingest.capture_active_market_snapshots", bind=True, base=BaseTask)
def capture_active_market_snapshots(
    self,
    triggered_at: str | None = None,
    market_limit: int | None = None,
) -> dict:
    service = get_polymarket_ingest_service()
    parsed_triggered_at = _parse_triggered_at(triggered_at)
    result = service.capture_snapshots(
        triggered_at=parsed_triggered_at,
        market_limit=market_limit,
    )
    logger.info(
        "snapshot capture completed",
        extra={"task_id": self.request.id},
    )
    return result
