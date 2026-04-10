"""Risk API schemas and serialization helpers."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RiskStateResponse(BaseModel):
    state: str
    history: list[dict[str, Any]] = Field(default_factory=list)


class ExposureItem(BaseModel):
    cluster_code: str
    gross_exposure: float
    net_exposure: float
    position_count: int
    limit_value: float
    utilization_rate: float
    is_breached: bool
    snapshot_at: str


class ExposureResponse(BaseModel):
    exposures: list[ExposureItem]


class KillSwitchCreateRequest(BaseModel):
    request_type: str  # freeze | risk_off | unfreeze
    target_scope: str  # global | cluster_code
    requested_by: str
    reason: str


class KillSwitchReviewRequest(BaseModel):
    reviewer: str
    notes: Optional[str] = None


class KillSwitchItem(BaseModel):
    id: str
    request_type: str
    target_scope: str
    requested_by: str
    reason: str
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    review_notes: Optional[str]
    created_at: str


class KillSwitchResponse(BaseModel):
    request: KillSwitchItem


class KillSwitchListResponse(BaseModel):
    requests: list[KillSwitchItem]


class ThresholdItem(BaseModel):
    id: str
    cluster_code: str
    metric_name: str
    threshold_value: float
    is_active: bool
    created_by: str
    created_at: str


class ThresholdListResponse(BaseModel):
    thresholds: list[ThresholdItem]


class ThresholdUpsertRequest(BaseModel):
    cluster_code: str
    metric_name: str
    threshold_value: float
    created_by: str


class ThresholdResponse(BaseModel):
    threshold: ThresholdItem


def format_state_event(
    event: Any,
    *,
    include_id: bool = False,
    include_threshold: bool = False,
) -> dict[str, Any]:
    payload = {
        "from_state": event.from_state,
        "to_state": event.to_state,
        "trigger_type": event.trigger_type,
        "trigger_metric": event.trigger_metric,
        "trigger_value": float(event.trigger_value),
        "actor_id": event.actor_id,
        "notes": event.notes,
        "created_at": event.created_at.isoformat(),
    }
    if include_id:
        payload["id"] = str(event.id)
    if include_threshold:
        payload["threshold_value"] = float(event.threshold_value)
    return payload


def format_exposure(exposure: Any) -> ExposureItem:
    return ExposureItem(
        cluster_code=exposure.cluster_code,
        gross_exposure=float(exposure.gross_exposure),
        net_exposure=float(exposure.net_exposure),
        position_count=exposure.position_count,
        limit_value=float(exposure.limit_value),
        utilization_rate=float(exposure.utilization_rate),
        is_breached=exposure.is_breached,
        snapshot_at=exposure.snapshot_at.isoformat(),
    )


def format_kill_switch_request(request: Any) -> KillSwitchItem:
    return KillSwitchItem(
        id=str(request.id),
        request_type=request.request_type,
        target_scope=request.target_scope,
        requested_by=request.requested_by,
        reason=request.reason,
        status=request.status,
        reviewed_by=request.reviewed_by,
        reviewed_at=request.reviewed_at.isoformat() if request.reviewed_at else None,
        review_notes=request.review_notes,
        created_at=request.created_at.isoformat(),
    )


def format_threshold(threshold: Any) -> ThresholdItem:
    return ThresholdItem(
        id=str(threshold.id),
        cluster_code=threshold.cluster_code,
        metric_name=threshold.metric_name,
        threshold_value=float(threshold.threshold_value),
        is_active=threshold.is_active,
        created_by=threshold.created_by,
        created_at=threshold.created_at.isoformat(),
    )
