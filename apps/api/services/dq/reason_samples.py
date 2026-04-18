from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from db.models import DataQualityResult


class DQReasonCheckPayload(BaseModel):
    code: str
    status: str
    severity: str
    message: str
    blocking: bool
    reason_code: str | None
    details: dict[str, Any] | list[Any] | None


class DQReasonTimestampsPayload(BaseModel):
    creation_time: str | None
    open_time: str | None
    close_time: str | None
    resolution_time: str | None
    source_updated_at: str | None
    latest_snapshot_time: str | None
    previous_snapshot_time: str | None


class DQReasonSamplePayload(BaseModel):
    market_ref_id: str
    market_id: str | None
    status: str
    score: float | None
    failure_count: int
    blocking_reason_codes: list[str]
    warning_reason_codes: list[str]
    matching_checks: list[DQReasonCheckPayload]
    timestamps: DQReasonTimestampsPayload


class DQReasonSamplesResponse(BaseModel):
    reason_code: str
    latest_checked_at: str | None
    total_matches: int
    samples: list[DQReasonSamplePayload]


def coerce_result_details(result: DataQualityResult) -> dict[str, Any]:
    details = result.result_details
    if isinstance(details, dict):
        return details
    return {}


def coerce_reason_codes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def extract_matching_checks(result_details: dict[str, Any], reason_code: str) -> list[DQReasonCheckPayload]:
    checks = result_details.get("checks")
    if not isinstance(checks, list):
        return []

    matches: list[DQReasonCheckPayload] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        if check.get("reason_code") != reason_code:
            continue
        matches.append(
            DQReasonCheckPayload(
                code=str(check.get("code") or ""),
                status=str(check.get("status") or "unknown"),
                severity=str(check.get("severity") or "unknown"),
                message=str(check.get("message") or ""),
                blocking=bool(check.get("blocking")),
                reason_code=str(check.get("reason_code")) if check.get("reason_code") else None,
                details=check.get("details"),
            )
        )
    return matches


def extract_snapshot_time(result_details: dict[str, Any], key: str) -> str | None:
    snapshot = result_details.get(key)
    if not isinstance(snapshot, dict):
        return None
    snapshot_time = snapshot.get("snapshot_time")
    if snapshot_time in (None, ""):
        return None
    return str(snapshot_time)
