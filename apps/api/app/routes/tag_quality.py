from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from services.tag_quality import TagQualityService

router = APIRouter(prefix="/tag-quality", tags=["tag-quality"])

class MetricsResponse(BaseModel):
    metrics: list[dict[str, Any]]

@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    request: Request,
    session: Session = Depends(get_db),
) -> MetricsResponse:
    """Get tag quality metrics."""
    service = TagQualityService(db=session)
    metrics = service.get_metrics()
    return MetricsResponse(metrics=metrics)
