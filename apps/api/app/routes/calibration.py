from __future__ import annotations
import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from services.calibration.service import CalibrationService


router = APIRouter(prefix="/calibration", tags=["calibration"])


class CalibrationUnitSchema(BaseModel):
    id: uuid.UUID
    price_bucket: str
    category_code: str
    time_bucket: str
    liquidity_tier: str
    window_type: str
    sample_count: int
    edge_estimate: float
    interval_low: float
    interval_high: float
    is_active: bool
    disabled_reason: Optional[str] = None
    computed_at: datetime

    class Config:
        from_attributes = True


class CalibrationComputeRequest(BaseModel):
    category_code: str
    price_bucket: str
    time_bucket: str
    liquidity_tier: str = "standard"
    window_type: str = "long"


@router.get("/units", response_model=List[CalibrationUnitSchema])
def list_units(session: Session = Depends(get_db)):
    """获取所有活跃的校准单元"""
    service = CalibrationService(session)
    return service.list_active_units()


@router.post("/compute", response_model=CalibrationUnitSchema)
def compute_unit(
    request: CalibrationComputeRequest,
    session: Session = Depends(get_db)
):
    """手动触发或更新校准计算"""
    service = CalibrationService(session)
    return service.compute_calibration(
        category_code=request.category_code,
        price_bucket=request.price_bucket,
        time_bucket=request.time_bucket,
        liquidity_tier=request.liquidity_tier,
        window_type=request.window_type
    )
