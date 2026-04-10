from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from db.models import AuditLog, DataQualityResult, Market, MarketSnapshot
from db.session import get_db


router = APIRouter(prefix="/dq", tags=["data-quality"])
settings = get_settings()


class DQReasonCount(BaseModel):
    reason_code: str
    count: int


class DQSnapshotCaptureSummary(BaseModel):
    triggered_at: str | None
    audited_at: str
    task_id: str | None
    selected_markets: int | None
    created: int | None
    skipped_existing: int | None
    skipped_missing_mapping: int | None
    skipped_missing_order_books: int | None
    book_fetch_failed_tokens: int
    created_from_source_payload: int
    source_payload_fallback_enabled: bool


class DQSummaryPayload(BaseModel):
    total_checks: int
    status_distribution: dict[str, int]
    pass_rate: float
    latest_checked_at: str | None
    latest_snapshot_time: str | None
    snapshot_age_seconds: int | None
    freshness_status: str
    top_blocking_reasons: list[DQReasonCount]
    latest_snapshot_capture: DQSnapshotCaptureSummary | None


class DQRecentResult(BaseModel):
    id: str
    market_ref_id: str
    market_id: str | None
    checked_at: str
    status: str
    score: float | None
    failure_count: int
    rule_version: str
    blocking_reason_codes: list[str]
    warning_reason_codes: list[str]


class DQSummaryResponse(BaseModel):
    summary: DQSummaryPayload
    recent_results: list[DQRecentResult]


class DQResultPayload(BaseModel):
    id: str
    market_ref_id: str
    checked_at: str
    status: str
    score: float | None
    failure_count: int
    result_details: dict[str, Any] | list[Any] | None
    rule_version: str
    created_at: str


class DQDetailResponse(BaseModel):
    result: DQResultPayload


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _summarize_reason_counts(results: list[DataQualityResult]) -> list[DQReasonCount]:
    counter: Counter[str] = Counter()
    for result in results:
        details = result.result_details or {}
        if not isinstance(details, dict):
            continue
        blocking_reason_codes = details.get("blocking_reason_codes") or []
        if isinstance(blocking_reason_codes, list):
            for reason_code in blocking_reason_codes:
                if reason_code:
                    counter[str(reason_code)] += 1

    return [
        DQReasonCount(reason_code=reason_code, count=count)
        for reason_code, count in counter.most_common(5)
    ]


def _latest_snapshot_capture_summary(session: Session) -> DQSnapshotCaptureSummary | None:
    latest_audit = session.scalar(
        select(AuditLog)
        .where(
            AuditLog.object_type == "market_snapshot_capture",
            AuditLog.action == "execute",
            AuditLog.result == "success",
        )
        .order_by(desc(AuditLog.created_at))
        .limit(1)
    )
    if latest_audit is None:
        return None

    payload = latest_audit.event_payload if isinstance(latest_audit.event_payload, dict) else {}
    return DQSnapshotCaptureSummary(
        triggered_at=latest_audit.object_id if latest_audit.object_id not in ("", "unknown") else None,
        audited_at=latest_audit.created_at.isoformat(),
        task_id=latest_audit.task_id,
        selected_markets=_coerce_int(payload.get("selected_markets")),
        created=_coerce_int(payload.get("created")),
        skipped_existing=_coerce_int(payload.get("skipped_existing")),
        skipped_missing_mapping=_coerce_int(payload.get("skipped_missing_mapping")),
        skipped_missing_order_books=_coerce_int(payload.get("skipped_missing_order_books")),
        book_fetch_failed_tokens=_coerce_int(payload.get("book_fetch_failed_tokens")) or 0,
        created_from_source_payload=_coerce_int(payload.get("created_from_source_payload")) or 0,
        source_payload_fallback_enabled=settings.ingest_allow_source_payload_fallback,
    )


def _empty_summary(snapshot_capture: DQSnapshotCaptureSummary | None) -> DQSummaryPayload:
    return DQSummaryPayload(
        total_checks=0,
        status_distribution={},
        pass_rate=0,
        latest_checked_at=None,
        latest_snapshot_time=None,
        snapshot_age_seconds=None,
        freshness_status="unknown",
        top_blocking_reasons=[],
        latest_snapshot_capture=snapshot_capture,
    )


@router.get("/summary", response_model=DQSummaryResponse)
def get_dq_summary(
    request: Request,
    session: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50, description="Number of recent results from the latest DQ batch"),
) -> DQSummaryResponse:
    """Get DQ summary statistics for the latest scan batch."""
    latest_snapshot_capture = _latest_snapshot_capture_summary(session)
    latest_checked_at = session.scalar(select(func.max(DataQualityResult.checked_at)))
    if latest_checked_at is None:
        return DQSummaryResponse(summary=_empty_summary(latest_snapshot_capture), recent_results=[])

    batch_results = list(
        session.scalars(
            select(DataQualityResult)
            .where(DataQualityResult.checked_at == latest_checked_at)
        ).all()
    )

    status_counts = Counter(result.status for result in batch_results)
    total_checks = len(batch_results)
    pass_rate = status_counts.get("pass", 0) / total_checks if total_checks else 0

    latest_snapshot_time = session.scalar(select(func.max(MarketSnapshot.snapshot_time)))
    latest_checked_at_utc = _ensure_utc(latest_checked_at)
    latest_snapshot_time_utc = _ensure_utc(latest_snapshot_time)
    snapshot_age_seconds: int | None = None
    freshness_status = "unknown"
    if latest_checked_at_utc and latest_snapshot_time_utc:
        snapshot_age_seconds = max(int((latest_checked_at_utc - latest_snapshot_time_utc).total_seconds()), 0)
        freshness_status = (
            "fresh"
            if snapshot_age_seconds <= settings.dq_snapshot_stale_after_seconds
            else "stale"
        )

    status_rank = case(
        (DataQualityResult.status == "fail", 0),
        (DataQualityResult.status == "warn", 1),
        else_=2,
    )
    recent_rows = session.execute(
        select(DataQualityResult, Market.market_id)
        .join(Market, Market.id == DataQualityResult.market_ref_id)
        .where(DataQualityResult.checked_at == latest_checked_at)
        .order_by(status_rank, desc(DataQualityResult.failure_count), DataQualityResult.score.asc(), Market.market_id)
        .limit(limit)
    ).all()

    recent_data: list[DQRecentResult] = []
    for result, market_id in recent_rows:
        result_details = result.result_details if isinstance(result.result_details, dict) else {}
        recent_data.append(
            DQRecentResult(
                id=str(result.id),
                market_ref_id=str(result.market_ref_id),
                market_id=market_id,
                checked_at=result.checked_at.isoformat(),
                status=result.status,
                score=float(result.score) if result.score is not None else None,
                failure_count=result.failure_count,
                rule_version=result.rule_version,
                blocking_reason_codes=result_details.get("blocking_reason_codes", []),
                warning_reason_codes=result_details.get("warning_reason_codes", []),
            )
        )

    summary = DQSummaryPayload(
        total_checks=total_checks,
        status_distribution=dict(status_counts),
        pass_rate=pass_rate,
        latest_checked_at=latest_checked_at.isoformat(),
        latest_snapshot_time=latest_snapshot_time.isoformat() if latest_snapshot_time is not None else None,
        snapshot_age_seconds=snapshot_age_seconds,
        freshness_status=freshness_status,
        top_blocking_reasons=_summarize_reason_counts(batch_results),
        latest_snapshot_capture=latest_snapshot_capture,
    )

    return DQSummaryResponse(summary=summary, recent_results=recent_data)


@router.get("/markets/{market_id}", response_model=DQDetailResponse)
def get_market_dq_result(
    request: Request,
    market_id: str,
    session: Session = Depends(get_db),
) -> DQDetailResponse:
    """Get latest DQ result for a specific market."""
    market = session.scalar(select(Market).where(Market.market_id == market_id))

    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    result = session.scalar(
        select(DataQualityResult)
        .where(DataQualityResult.market_ref_id == market.id)
        .order_by(desc(DataQualityResult.checked_at))
        .limit(1)
    )

    if not result:
        raise HTTPException(status_code=404, detail="No DQ result found for this market")

    result_data = DQResultPayload(
        id=str(result.id),
        market_ref_id=str(result.market_ref_id),
        checked_at=result.checked_at.isoformat(),
        status=result.status,
        score=float(result.score) if result.score is not None else None,
        failure_count=result.failure_count,
        result_details=result.result_details,
        rule_version=result.rule_version,
        created_at=result.created_at.isoformat(),
    )

    return DQDetailResponse(result=result_data)
