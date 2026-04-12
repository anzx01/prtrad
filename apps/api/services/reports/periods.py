from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class ReportWindow:
    period_start: datetime
    period_end: datetime


def normalize_reference_time(reference_time: datetime | None) -> datetime:
    current = reference_time or datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def resolve_report_window(
    *,
    report_type: str,
    reference_time: datetime | None = None,
    days_override: int | None = None,
) -> ReportWindow:
    current = normalize_reference_time(reference_time)
    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)

    if report_type == "daily_summary":
        period_days = max(1, days_override or 1)
        return ReportWindow(period_start=day_start - timedelta(days=period_days), period_end=day_start)

    if report_type == "weekly_summary":
        period_days = max(1, days_override or 7)
        return ReportWindow(period_start=day_start - timedelta(days=period_days), period_end=day_start)

    if report_type == "stage_review":
        return ReportWindow(period_start=day_start, period_end=day_start + timedelta(days=1))

    raise ValueError("report_type must be one of daily_summary, weekly_summary, stage_review")
