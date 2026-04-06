"""风控路由：风险状态、暴露、kill-switch、阈值"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from services.risk.service import RiskService
from services.risk.kill_switch import KillSwitchService

router = APIRouter(prefix="/risk", tags=["risk"])


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class RiskStateResponse(BaseModel):
    state: str
    history: list[dict[str, Any]] = []


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
    request_type: str   # freeze | risk_off | unfreeze
    target_scope: str   # global | cluster_code
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_ks(req) -> KillSwitchItem:
    return KillSwitchItem(
        id=str(req.id),
        request_type=req.request_type,
        target_scope=req.target_scope,
        requested_by=req.requested_by,
        reason=req.reason,
        status=req.status,
        reviewed_by=req.reviewed_by,
        reviewed_at=req.reviewed_at.isoformat() if req.reviewed_at else None,
        review_notes=req.review_notes,
        created_at=req.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# 风险状态
# ---------------------------------------------------------------------------

@router.get("/state", response_model=RiskStateResponse)
def get_risk_state(session: Session = Depends(get_db)) -> RiskStateResponse:
    svc = RiskService(session)
    state = svc.get_current_state()
    events = svc.list_state_events(limit=10)
    history = [
        {
            "from_state": e.from_state,
            "to_state": e.to_state,
            "trigger_type": e.trigger_type,
            "trigger_metric": e.trigger_metric,
            "trigger_value": float(e.trigger_value),
            "actor_id": e.actor_id,
            "notes": e.notes,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
    return RiskStateResponse(state=state, history=history)


@router.get("/state/history")
def get_state_history(limit: int = 50, session: Session = Depends(get_db)):
    svc = RiskService(session)
    events = svc.list_state_events(limit=limit)
    return {
        "events": [
            {
                "id": str(e.id),
                "from_state": e.from_state,
                "to_state": e.to_state,
                "trigger_type": e.trigger_type,
                "trigger_metric": e.trigger_metric,
                "trigger_value": float(e.trigger_value),
                "threshold_value": float(e.threshold_value),
                "actor_id": e.actor_id,
                "notes": e.notes,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
    }


# ---------------------------------------------------------------------------
# 风险暴露
# ---------------------------------------------------------------------------

@router.get("/exposures", response_model=ExposureResponse)
def get_exposures(
    cluster_code: Optional[str] = None,
    session: Session = Depends(get_db),
) -> ExposureResponse:
    svc = RiskService(session)
    exposures = svc.list_exposures(cluster_code=cluster_code)
    return ExposureResponse(
        exposures=[
            ExposureItem(
                cluster_code=e.cluster_code,
                gross_exposure=float(e.gross_exposure),
                net_exposure=float(e.net_exposure),
                position_count=e.position_count,
                limit_value=float(e.limit_value),
                utilization_rate=float(e.utilization_rate),
                is_breached=e.is_breached,
                snapshot_at=e.snapshot_at.isoformat(),
            )
            for e in exposures
        ]
    )


@router.post("/exposures/compute", response_model=ExposureResponse)
def compute_exposures(
    cluster_code: Optional[str] = None,
    session: Session = Depends(get_db),
) -> ExposureResponse:
    svc = RiskService(session)
    exposures = svc.compute_exposure(cluster_code=cluster_code)
    # 也尝试自动状态迁移
    svc.check_and_auto_transition()
    session.commit()
    return ExposureResponse(
        exposures=[
            ExposureItem(
                cluster_code=e.cluster_code,
                gross_exposure=float(e.gross_exposure),
                net_exposure=float(e.net_exposure),
                position_count=e.position_count,
                limit_value=float(e.limit_value),
                utilization_rate=float(e.utilization_rate),
                is_breached=e.is_breached,
                snapshot_at=e.snapshot_at.isoformat(),
            )
            for e in exposures
        ]
    )


# ---------------------------------------------------------------------------
# Kill-Switch
# ---------------------------------------------------------------------------

@router.get("/kill-switch", response_model=KillSwitchListResponse)
def list_kill_switch_requests(
    status: Optional[str] = None,
    session: Session = Depends(get_db),
) -> KillSwitchListResponse:
    svc = KillSwitchService(session)
    reqs = svc.list_requests(status=status)
    return KillSwitchListResponse(requests=[_format_ks(r) for r in reqs])


@router.post("/kill-switch", response_model=KillSwitchResponse)
def create_kill_switch_request(
    body: KillSwitchCreateRequest,
    session: Session = Depends(get_db),
) -> KillSwitchResponse:
    valid_types = {"freeze", "risk_off", "unfreeze"}
    if body.request_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"request_type must be one of {valid_types}")
    svc = KillSwitchService(session)
    req = svc.request_action(
        request_type=body.request_type,
        target_scope=body.target_scope,
        requested_by=body.requested_by,
        reason=body.reason,
    )
    session.commit()
    return KillSwitchResponse(request=_format_ks(req))


@router.post("/kill-switch/{request_id}/approve", response_model=KillSwitchResponse)
def approve_kill_switch(
    request_id: uuid.UUID,
    body: KillSwitchReviewRequest,
    session: Session = Depends(get_db),
) -> KillSwitchResponse:
    svc = KillSwitchService(session)
    try:
        req = svc.approve(request_id, reviewer=body.reviewer, notes=body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    session.commit()
    return KillSwitchResponse(request=_format_ks(req))


@router.post("/kill-switch/{request_id}/reject", response_model=KillSwitchResponse)
def reject_kill_switch(
    request_id: uuid.UUID,
    body: KillSwitchReviewRequest,
    session: Session = Depends(get_db),
) -> KillSwitchResponse:
    svc = KillSwitchService(session)
    try:
        req = svc.reject(request_id, reviewer=body.reviewer, notes=body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    session.commit()
    return KillSwitchResponse(request=_format_ks(req))


# ---------------------------------------------------------------------------
# 阈值配置
# ---------------------------------------------------------------------------

@router.get("/thresholds", response_model=ThresholdListResponse)
def list_thresholds(session: Session = Depends(get_db)) -> ThresholdListResponse:
    svc = RiskService(session)
    thresholds = svc.list_thresholds()
    return ThresholdListResponse(
        thresholds=[
            ThresholdItem(
                id=str(t.id),
                cluster_code=t.cluster_code,
                metric_name=t.metric_name,
                threshold_value=float(t.threshold_value),
                is_active=t.is_active,
                created_by=t.created_by,
                created_at=t.created_at.isoformat(),
            )
            for t in thresholds
        ]
    )
