from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from services.monitoring import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

class MetricsResponse(BaseModel):
    metrics: dict[str, Any]

@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    request: Request,
    session: Session = Depends(get_db),
) -> MetricsResponse:
    """Get monitoring metrics."""
    service = MonitoringService(db=session)
    result = service.get_metrics()
    # service returns { status, metrics: {...} }, unwrap to flat structure
    return MetricsResponse(metrics=result.get("metrics", result))
