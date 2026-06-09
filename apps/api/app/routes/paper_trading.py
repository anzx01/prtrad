from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from services.paper_trading import PaperTradingService


router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])


class PaperEvaluateRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
    strategy_version: str | None = None


class PaperMarkRequest(BaseModel):
    auto_close: bool = True


class PaperSummaryResponse(BaseModel):
    summary: dict[str, Any]


class PaperPositionsResponse(BaseModel):
    positions: list[dict[str, Any]]


class PaperEvaluateResponse(BaseModel):
    result: dict[str, Any]
    summary: dict[str, Any]


class PaperMarkResponse(BaseModel):
    result: dict[str, Any]
    summary: dict[str, Any]


@router.get("/summary", response_model=PaperSummaryResponse)
def get_paper_summary(session: Session = Depends(get_db)) -> PaperSummaryResponse:
    service = PaperTradingService(session)
    return PaperSummaryResponse(summary=service.get_summary())


@router.get("/positions", response_model=PaperPositionsResponse)
def list_paper_positions(
    status: str | None = Query(default=None, description="open | closed"),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db),
) -> PaperPositionsResponse:
    service = PaperTradingService(session)
    positions = [service.serialize_position(position) for position in service.list_positions(status=status, limit=limit)]
    return PaperPositionsResponse(positions=positions)


@router.post("/evaluate", response_model=PaperEvaluateResponse)
def evaluate_paper_candidates(
    body: PaperEvaluateRequest,
    session: Session = Depends(get_db),
) -> PaperEvaluateResponse:
    service = PaperTradingService(session)
    result = service.evaluate_candidates(limit=body.limit, strategy_version=body.strategy_version)
    session.commit()
    return PaperEvaluateResponse(result=result, summary=service.get_summary())


@router.post("/mark", response_model=PaperMarkResponse)
def mark_paper_positions(
    body: PaperMarkRequest | None = None,
    session: Session = Depends(get_db),
) -> PaperMarkResponse:
    service = PaperTradingService(session)
    payload = body or PaperMarkRequest()
    result = service.mark_positions(auto_close=payload.auto_close)
    session.commit()
    return PaperMarkResponse(result=result, summary=service.get_summary())
