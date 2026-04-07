from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from services.netev.service import NetEVService


router = APIRouter(prefix="/netev", tags=["netev"])


class NetEVCandidateSchema(BaseModel):
    id: uuid.UUID
    market_ref_id: uuid.UUID
    market_id: str | None = None
    question: str | None = None
    category_code: str | None = None
    calibration_unit_id: uuid.UUID | None = None
    calibration_sample_count: int | None = None
    price_bucket: str | None = None
    time_bucket: str | None = None
    liquidity_tier: str | None = None
    window_type: str | None = None
    gross_edge: float
    fee_cost: float
    slippage_cost: float
    dispute_discount: float
    net_ev: float
    admission_decision: str
    rejection_reason_code: str | None = None
    rejection_reason_name: str | None = None
    rejection_reason_description: str | None = None
    scoring_recommendation: str | None = None
    dq_status: str | None = None
    rule_version: str
    evaluated_at: datetime


class NetEVBatchResponse(BaseModel):
    total: int
    admitted: int
    rejected: int
    candidates: list[NetEVCandidateSchema]


@router.get("/candidates", response_model=list[NetEVCandidateSchema])
def list_candidates(
    decision: str | None = Query(None, description="admit | reject"),
    session: Session = Depends(get_db),
):
    service = NetEVService(session)
    return service.list_candidate_views(decision=decision)


@router.post("/evaluate/{market_id}", response_model=NetEVCandidateSchema)
def evaluate_market(
    market_id: uuid.UUID,
    window_type: str = Query("long", pattern="^(short|long)$"),
    session: Session = Depends(get_db),
):
    service = NetEVService(session)
    result = service.evaluate(market_id, window_type=window_type)
    if not result:
        raise HTTPException(status_code=404, detail="Market not found")
    return service.get_candidate_view(result)


@router.post("/evaluate-batch", response_model=NetEVBatchResponse)
def evaluate_batch(
    limit: int = Query(20, ge=1, le=200),
    window_type: str = Query("long", pattern="^(short|long)$"),
    session: Session = Depends(get_db),
):
    service = NetEVService(session)
    candidates = service.evaluate_batch(limit=limit, window_type=window_type)
    candidate_views = [service.get_candidate_view(candidate) for candidate in candidates]
    admitted = sum(1 for candidate in candidate_views if candidate["admission_decision"] == "admit")
    return NetEVBatchResponse(
        total=len(candidate_views),
        admitted=admitted,
        rejected=len(candidate_views) - admitted,
        candidates=candidate_views,
    )
