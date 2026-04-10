"""风控路由：风险状态、暴露、kill-switch、阈值"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.risk_api import (
    ExposureResponse,
    KillSwitchCreateRequest,
    KillSwitchListResponse,
    KillSwitchReviewRequest,
    KillSwitchResponse,
    RiskStateResponse,
    ThresholdListResponse,
    ThresholdResponse,
    ThresholdUpsertRequest,
    format_exposure,
    format_kill_switch_request,
    format_state_event,
    format_threshold,
)
from db.session import get_db
from services.risk.kill_switch import KillSwitchService
from services.risk.service import RiskService

router = APIRouter(prefix="/risk", tags=["risk"])


# ---------------------------------------------------------------------------
# 风险状态
# ---------------------------------------------------------------------------

@router.get("/state", response_model=RiskStateResponse)
def get_risk_state(session: Session = Depends(get_db)) -> RiskStateResponse:
    svc = RiskService(session)
    state = svc.get_current_state()
    events = svc.list_state_events(limit=10)
    history = [format_state_event(event) for event in events]
    return RiskStateResponse(state=state, history=history)


@router.get("/state/history")
def get_state_history(limit: int = 50, session: Session = Depends(get_db)):
    svc = RiskService(session)
    events = svc.list_state_events(limit=limit)
    return {"events": [format_state_event(event, include_id=True, include_threshold=True) for event in events]}


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
    return ExposureResponse(exposures=[format_exposure(exposure) for exposure in exposures])


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
    return ExposureResponse(exposures=[format_exposure(exposure) for exposure in exposures])


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
    return KillSwitchListResponse(requests=[format_kill_switch_request(request) for request in reqs])


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
    return KillSwitchResponse(request=format_kill_switch_request(req))


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
    return KillSwitchResponse(request=format_kill_switch_request(req))


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
    return KillSwitchResponse(request=format_kill_switch_request(req))


# ---------------------------------------------------------------------------
# 阈值配置
# ---------------------------------------------------------------------------

@router.get("/thresholds", response_model=ThresholdListResponse)
def list_thresholds(session: Session = Depends(get_db)) -> ThresholdListResponse:
    svc = RiskService(session)
    thresholds = svc.list_thresholds()
    return ThresholdListResponse(thresholds=[format_threshold(threshold) for threshold in thresholds])


@router.post("/thresholds", response_model=ThresholdResponse)
def upsert_threshold(
    body: ThresholdUpsertRequest,
    session: Session = Depends(get_db),
) -> ThresholdResponse:
    svc = RiskService(session)

    try:
        threshold = svc.upsert_threshold(
            cluster_code=body.cluster_code,
            metric_name=body.metric_name,
            threshold_value=Decimal(str(body.threshold_value)),
            created_by=body.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session.commit()
    return ThresholdResponse(threshold=format_threshold(threshold))


@router.post("/thresholds/{threshold_id}/deactivate", response_model=ThresholdResponse)
def deactivate_threshold(
    threshold_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> ThresholdResponse:
    svc = RiskService(session)

    try:
        threshold = svc.deactivate_threshold(threshold_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    session.commit()
    return ThresholdResponse(threshold=format_threshold(threshold))
