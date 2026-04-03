from __future__ import annotations

import logging
from datetime import UTC, datetime

from common import record_worker_audit_event
from services.tagging import get_market_auto_classification_service
from worker.celery_app import celery_app
from worker.tasks.base import BaseTask


logger = logging.getLogger("ptr.worker.tagging")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_classified_at(value: str | None) -> datetime:
    """Parse classified_at timestamp with error handling."""
    try:
        if not value:
            return datetime.now(UTC).replace(microsecond=0)
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse classified_at value: {value}", exc_info=True)
        raise ValueError(f"Invalid classified_at format: {value}") from e


@celery_app.task(name="worker.tagging.dispatch_market_auto_classification", bind=True, base=BaseTask)
def dispatch_market_auto_classification(self) -> dict[str, str]:
    classified_at = _utc_now_iso()
    async_result = run_market_auto_classification.apply_async(kwargs={"classified_at": classified_at})
    record_worker_audit_event(
        object_type="market_auto_tagging",
        object_id=classified_at,
        action="dispatch",
        result="queued",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={"dispatched_task_id": async_result.id},
    )
    logger.info(
        "market auto classification dispatched",
        extra={"task_id": self.request.id},
    )
    return {
        "status": "queued",
        "classified_at": classified_at,
        "dispatched_task_id": async_result.id,
    }


@celery_app.task(name="worker.tagging.run_market_auto_classification", bind=True, base=BaseTask)
def run_market_auto_classification(
    self,
    classified_at: str | None = None,
    market_limit: int | None = None,
) -> dict:
    service = get_market_auto_classification_service()
    parsed_classified_at = _parse_classified_at(classified_at)
    result = service.classify_markets(
        classified_at=parsed_classified_at,
        market_limit=market_limit,
    )
    record_worker_audit_event(
        object_type="market_auto_tagging",
        object_id=parsed_classified_at.isoformat(),
        action="execute",
        result="success",
        task_id=self.request.id,
        actor_id=self.name,
        event_payload={
            "selected_markets": result.get("selected_markets"),
            "created": result.get("created"),
            "skipped_existing": result.get("skipped_existing"),
            "tagged": result.get("Tagged"),
            "review_required": result.get("ReviewRequired"),
            "blocked": result.get("Blocked"),
            "classification_failed": result.get("ClassificationFailed"),
            "review_tasks_created": result.get("review_tasks_created"),
        },
    )
    for sample in result.get("sample_results", []):
        logger.info(
            "market auto classification sample market=%s status=%s category=%s bucket=%s",
            sample.get("market_id"),
            sample.get("classification_status"),
            sample.get("primary_category_code"),
            sample.get("admission_bucket_code"),
            extra={"task_id": self.request.id},
        )
    logger.info(
        "market auto classification completed",
        extra={"task_id": self.request.id},
    )
    return result
