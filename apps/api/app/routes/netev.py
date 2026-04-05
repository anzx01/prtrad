from __future__ import annotations
import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from services.netev.service import NetEVService


router = APIRouter(prefix="/netev", tags=["netev"])


class NetEVCandidateSchema(BaseModel):
    id: uuid.UUID
    market_ref_id: uuid.UUID
    calibration_unit_id: Optional[uuid.UUID] = None
    gross_edge: float
    fee_cost: float
    slippage_cost: float
    dispute_discount: float
    net_ev: float
    admission_decision: str
    rejection_reason_code: Optional[str] = None
    evaluated_at: datetime

    class Config:
        from_attributes = True


@router.get("/candidates", response_model=List[NetEVCandidateSchema])
def list_candidates(
    decision: Optional[str] = Query(None, description="admit | reject"),
    session: Session = Depends(get_db)
):
    """获取所有准入评估候选记录"""
    service = NetEVService(session)
    return service.list_candidates(decision=decision)


@router.post("/evaluate/{market_id}", response_model=NetEVCandidateSchema)
def evaluate_market(
    market_id: uuid.UUID,
    session: Session = Depends(get_db)
):
    """评估特定市场的 NetEV 准入状态"""
    service = NetEVService(session)
    result = service.evaluate(market_id)
    if not result:
        raise HTTPException(status_code=404, detail="Market not found")
    return result
