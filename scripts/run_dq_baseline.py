from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import case, desc, func, select


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
for extra_path in (ROOT / "apps" / "api", ROOT / "workers"):
    path_str = str(extra_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.config import get_settings
from common import record_worker_audit_event
from db.models import DataQualityResult, Market, MarketSnapshot
from db.session import session_scope
from services.audit import AuditEvent, get_audit_log_service
from services.dq import get_market_dq_service
from services.dq.reason_samples import (
    DQReasonSamplePayload,
    DQReasonTimestampsPayload,
    coerce_reason_codes,
    coerce_result_details,
    extract_matching_checks,
    extract_snapshot_time,
    summarize_matching_check_counts,
    summarize_missing_field_counts,
)
from services.ingest import get_polymarket_ingest_service


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _configure_logging() -> None:
    logging.basicConfig(level=logging.CRITICAL)
    for logger_name in (
        "ptr.audit",
        "ptr.worker",
        "ptr.worker.ingest",
        "ptr.worker.dq",
        "services.ingest",
        "services.dq",
    ):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def _summarize_reason_counts(results: list[DataQualityResult]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for result in results:
        result_details = coerce_result_details(result)
        for reason_code in coerce_reason_codes(result_details.get("blocking_reason_codes")):
            if reason_code:
                counter[str(reason_code)] += 1

    return [
        {"reason_code": reason_code, "count": count}
        for reason_code, count in counter.most_common(5)
    ]


def _build_batch_summary(checked_at: datetime) -> dict[str, Any]:
    settings = get_settings()
    with session_scope() as session:
        batch_results = list(
            session.scalars(
                select(DataQualityResult).where(DataQualityResult.checked_at == checked_at)
            ).all()
        )
        latest_snapshot_time = session.scalar(select(func.max(MarketSnapshot.snapshot_time)))
        status_counts = Counter(result.status for result in batch_results)
        total_checks = len(batch_results)
        pass_rate = status_counts.get("pass", 0) / total_checks if total_checks else 0.0

        latest_snapshot_time_utc = _ensure_utc(latest_snapshot_time)
        checked_at_utc = _ensure_utc(checked_at)
        snapshot_age_seconds: int | None = None
        freshness_status = "unknown"
        if checked_at_utc and latest_snapshot_time_utc:
            snapshot_age_seconds = max(int((checked_at_utc - latest_snapshot_time_utc).total_seconds()), 0)
            freshness_status = (
                "fresh"
                if snapshot_age_seconds <= settings.dq_snapshot_stale_after_seconds
                else "stale"
            )

        return {
            "checked_at": checked_at.isoformat(),
            "total_checks": total_checks,
            "status_distribution": dict(status_counts),
            "pass_rate": pass_rate,
            "latest_snapshot_time": latest_snapshot_time.isoformat() if latest_snapshot_time is not None else None,
            "snapshot_age_seconds": snapshot_age_seconds,
            "freshness_status": freshness_status,
            "top_blocking_reasons": _summarize_reason_counts(batch_results),
        }


def _build_reason_focus(checked_at: datetime, reason_code: str, limit: int) -> dict[str, Any]:
    with session_scope() as session:
        status_rank = case(
            (DataQualityResult.status == "fail", 0),
            (DataQualityResult.status == "warn", 1),
            else_=2,
        )
        rows = session.execute(
            select(DataQualityResult, Market)
            .join(Market, Market.id == DataQualityResult.market_ref_id)
            .where(DataQualityResult.checked_at == checked_at)
            .order_by(status_rank, desc(DataQualityResult.failure_count), DataQualityResult.score.asc(), Market.market_id)
        ).all()
        samples: list[DQReasonSamplePayload] = []
        for result, market in rows:
            result_details = coerce_result_details(result)
            blocking_reason_codes = coerce_reason_codes(result_details.get("blocking_reason_codes"))
            warning_reason_codes = coerce_reason_codes(result_details.get("warning_reason_codes"))
            matching_checks = extract_matching_checks(result_details, reason_code)
            if reason_code not in blocking_reason_codes and reason_code not in warning_reason_codes and not matching_checks:
                continue

            samples.append(
                DQReasonSamplePayload(
                    market_ref_id=str(result.market_ref_id),
                    market_id=market.market_id,
                    status=result.status,
                    score=float(result.score) if result.score is not None else None,
                    failure_count=result.failure_count,
                    blocking_reason_codes=blocking_reason_codes,
                    warning_reason_codes=warning_reason_codes,
                    matching_checks=matching_checks,
                    timestamps=DQReasonTimestampsPayload(
                        creation_time=_ensure_utc(market.creation_time).isoformat() if market.creation_time else None,
                        open_time=_ensure_utc(market.open_time).isoformat() if market.open_time else None,
                        close_time=_ensure_utc(market.close_time).isoformat() if market.close_time else None,
                        resolution_time=_ensure_utc(market.resolution_time).isoformat() if market.resolution_time else None,
                        source_updated_at=_ensure_utc(market.source_updated_at).isoformat()
                        if market.source_updated_at
                        else None,
                        latest_snapshot_time=extract_snapshot_time(result_details, "latest_snapshot"),
                        previous_snapshot_time=extract_snapshot_time(result_details, "previous_snapshot"),
                    ),
                )
            )

        return {
            "reason_code": reason_code,
            "checked_at": checked_at.isoformat(),
            "total_matches": len(samples),
            "check_counts": [item.model_dump(mode="json") for item in summarize_matching_check_counts(samples)],
            "missing_field_counts": [item.model_dump(mode="json") for item in summarize_missing_field_counts(samples)],
            "samples": [sample.model_dump(mode="json") for sample in samples[:limit]],
        }


def _record_snapshot_capture_audit(triggered_at: datetime, capture_result: dict[str, Any]) -> None:
    record_worker_audit_event(
        object_type="market_snapshot_capture",
        object_id=triggered_at.isoformat(),
        action="execute",
        result="success",
        task_id=None,
        actor_id="scripts.run_dq_baseline",
        event_payload={
            "selected_markets": capture_result.get("selected_markets"),
            "created": capture_result.get("created"),
            "skipped_existing": capture_result.get("skipped_existing"),
            "skipped_missing_mapping": capture_result.get("skipped_missing_mapping"),
            "skipped_missing_order_books": capture_result.get("skipped_missing_order_books"),
            "book_fetch_failed_tokens": capture_result.get("book_fetch_failed_tokens"),
            "created_from_source_payload": capture_result.get("created_from_source_payload"),
        },
    )


def _record_dq_scan_audit(checked_at: datetime, dq_result: dict[str, Any]) -> None:
    record_worker_audit_event(
        object_type="market_dq_scan",
        object_id=checked_at.isoformat(),
        action="execute",
        result="success",
        task_id=None,
        actor_id="scripts.run_dq_baseline",
        event_payload={
            "selected_markets": dq_result.get("selected_markets"),
            "created": dq_result.get("created"),
            "pass": dq_result.get("pass"),
            "warn": dq_result.get("warn"),
            "fail": dq_result.get("fail"),
            "alerts_emitted": dq_result.get("alerts_emitted"),
        },
    )


def _record_baseline_audit(
    *,
    checked_at: datetime | None,
    triggered_at: datetime | None,
    market_limit: int | None,
    reason_code: str,
    capture_result: dict[str, Any] | None,
    dq_result: dict[str, Any] | None,
    summary: dict[str, Any] | None,
    reason_focus: dict[str, Any] | None,
    error: str | None = None,
) -> None:
    audit_service = get_audit_log_service()
    object_id = checked_at.isoformat() if checked_at is not None else (triggered_at.isoformat() if triggered_at else "unknown")
    result = "failed" if error else "success"
    payload: dict[str, Any] = {
        "triggered_at": triggered_at.isoformat() if triggered_at is not None else None,
        "checked_at": checked_at.isoformat() if checked_at is not None else None,
        "market_limit": market_limit,
        "reason_code": reason_code,
        "capture": capture_result,
        "dq": dq_result,
        "summary": summary,
        "reason_focus": reason_focus,
    }
    if error:
        payload["error"] = error

    audit_service.safe_write_event(
        AuditEvent(
            actor_id="scripts.run_dq_baseline",
            actor_type="system",
            object_type="dq_baseline_check",
            object_id=object_id,
            action="execute",
            result=result,
            event_payload=payload,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run synchronous snapshot + DQ baseline and emit JSON summary."
    )
    parser.add_argument("--market-limit", type=int, default=0, help="Optional market limit for snapshot and DQ.")
    parser.add_argument("--reason-code", default="REJ_DATA_INCOMPLETE", help="Reason code to summarize.")
    parser.add_argument("--reason-limit", type=int, default=10, help="Number of samples to include in reason focus output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _configure_logging()

    effective_market_limit = args.market_limit if args.market_limit and args.market_limit > 0 else None
    triggered_at: datetime | None = None
    checked_at: datetime | None = None
    capture_result: dict[str, Any] | None = None
    dq_result: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    reason_focus: dict[str, Any] | None = None

    try:
        ingest_service = get_polymarket_ingest_service()
        dq_service = get_market_dq_service()

        triggered_at = _utc_now()
        capture_result = ingest_service.capture_snapshots(
            triggered_at=triggered_at,
            market_limit=effective_market_limit,
        )
        _record_snapshot_capture_audit(triggered_at, capture_result)

        checked_at = _utc_now()
        dq_result = dq_service.evaluate_markets(
            checked_at=checked_at,
            market_limit=effective_market_limit,
        )
        _record_dq_scan_audit(checked_at, dq_result)

        summary = _build_batch_summary(checked_at)
        reason_focus = _build_reason_focus(checked_at, args.reason_code, args.reason_limit)

        payload = {
            "triggered_at": triggered_at.isoformat(),
            "checked_at": checked_at.isoformat(),
            "market_limit": effective_market_limit,
            "capture": capture_result,
            "dq": dq_result,
            "summary": summary,
            "reason_focus": reason_focus,
        }
        _record_baseline_audit(
            checked_at=checked_at,
            triggered_at=triggered_at,
            market_limit=effective_market_limit,
            reason_code=args.reason_code,
            capture_result=capture_result,
            dq_result=dq_result,
            summary=summary,
            reason_focus=reason_focus,
        )
        json.dump(payload, sys.stdout, ensure_ascii=True)
        sys.stdout.write("\n")
        return 0
    except Exception as exc:
        _record_baseline_audit(
            checked_at=checked_at,
            triggered_at=triggered_at,
            market_limit=effective_market_limit,
            reason_code=args.reason_code,
            capture_result=capture_result,
            dq_result=dq_result,
            summary=summary,
            reason_focus=reason_focus,
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
