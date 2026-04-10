from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from db.session import get_db
from services.calibration.service import CalibrationService
from services.m3_helpers import utc_now


router = APIRouter(prefix="/calibration", tags=["calibration"])


class CalibrationUnitSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    disabled_reason: str | None = None
    computed_at: datetime


class CalibrationComputeRequest(BaseModel):
    category_code: str
    price_bucket: str
    time_bucket: str
    liquidity_tier: str = "standard"
    window_type: str = "long"


class CalibrationRecomputeResponse(BaseModel):
    window_type: str
    computed_at: datetime
    total_units: int
    active_units: int
    inactive_units: int


@router.get("/units", response_model=list[CalibrationUnitSchema])
def list_units(
    include_inactive: bool = Query(False, description="Whether to include inactive calibration units"),
    session: Session = Depends(get_db),
):
    service = CalibrationService(session)
    return service.list_units(include_inactive=include_inactive)


@router.post("/compute", response_model=CalibrationUnitSchema)
def compute_unit(
    request: CalibrationComputeRequest,
    session: Session = Depends(get_db),
):
    service = CalibrationService(session)
    return service.compute_calibration(
        category_code=request.category_code,
        price_bucket=request.price_bucket,
        time_bucket=request.time_bucket,
        liquidity_tier=request.liquidity_tier,
        window_type=request.window_type,
    )


@router.post("/recompute-all", response_model=CalibrationRecomputeResponse)
def recompute_all_units(
    window_type: str = Query("long", pattern="^(short|long)$"),
    session: Session = Depends(get_db),
):
    service = CalibrationService(session)
    units = service.recompute_all(window_type=window_type)
    active_units = sum(1 for unit in units if unit.is_active)
    return CalibrationRecomputeResponse(
        window_type=window_type,
        computed_at=utc_now(),
        total_units=len(units),
        active_units=active_units,
        inactive_units=len(units) - active_units,
    )
