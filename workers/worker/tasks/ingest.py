from __future__ import annotations

import logging
from datetime import UTC, datetime

from services.ingest import get_polymarket_ingest_service
from common import record_worker_audit_event
from worker.celery_app import celery_app
from worker.tasks.base import BaseTask


logger = logging.getLogger("ptr.worker.ingest")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_triggered_at(value: str | None) -> datetime:
    """Parse triggered_at timestamp with error handling."""
    try:
        if not value:
            return datetime.now(UTC).replace(microsecond=0)
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse triggered_at value: {value}", exc_info=True)
        raise ValueError(f"Invalid triggered_at format: {value}") from e


@celery_app.task(name="worker.ingest.dispatch_market_sync", bind=True, base=BaseTask)
def dispatch_market_sync(self) -> dict[str, str]:
    triggered_at = _utc_now_iso()
    async_result = run_market_catalog_sync.apply_async(kwargs={"triggered_at": triggered_at})
    record_worker_audit_event(
        object_type="market_catalog_sync",
        object_id=triggered_at,
        action="dispatch",
        result="queued",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={"dispatched_task_id": async_result.id},
    )
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
    record_worker_audit_event(
        object_type="market_catalog_sync",
        object_id=parsed_triggered_at.isoformat(),
        action="execute",
        result="success",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={
            "pages": result.get("pages"),
            "fetched_markets": result.get("fetched_markets"),
            "created": result.get("created"),
            "updated": result.get("updated"),
            "skipped_unchanged": result.get("skipped_unchanged"),
            "marked_inactive": result.get("marked_inactive"),
        },
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
    record_worker_audit_event(
        object_type="market_snapshot_capture",
        object_id=triggered_at,
        action="dispatch",
        result="queued",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={"dispatched_task_id": async_result.id},
    )
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
    record_worker_audit_event(
        object_type="market_snapshot_capture",
        object_id=parsed_triggered_at.isoformat(),
        action="execute",
        result="success",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={
            "selected_markets": result.get("selected_markets"),
            "created": result.get("created"),
            "skipped_existing": result.get("skipped_existing"),
            "skipped_missing_mapping": result.get("skipped_missing_mapping"),
            "skipped_missing_order_books": result.get("skipped_missing_order_books"),
        },
    )
    logger.info(
        "snapshot capture completed",
        extra={"task_id": self.request.id},
    )
    return result
