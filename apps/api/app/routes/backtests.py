from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from services.backtests import BacktestService


router = APIRouter(prefix="/backtests", tags=["backtests"])


class BacktestRunRequest(BaseModel):
    run_name: str = ""
    window_days: int = Field(default=30, ge=1, le=365)
    executed_by: str | None = None
    strategy_version: str | None = None


class BacktestRunResponse(BaseModel):
    run: dict[str, Any]


class BacktestRunListResponse(BaseModel):
    runs: list[dict[str, Any]]


@router.get("", response_model=BacktestRunListResponse)
def list_backtests(limit: int = 20, session: Session = Depends(get_db)) -> BacktestRunListResponse:
    service = BacktestService(session)
    runs = [service.serialize_run(run) for run in service.list_runs(limit=limit)]
    return BacktestRunListResponse(runs=runs)


@router.post("/run", response_model=BacktestRunResponse)
def create_backtest_run(
    body: BacktestRunRequest,
    session: Session = Depends(get_db),
) -> BacktestRunResponse:
    service = BacktestService(session)
    run = service.create_run(
        run_name=body.run_name,
        window_days=body.window_days,
        executed_by=body.executed_by,
        strategy_version=body.strategy_version,
    )
    session.commit()
    return BacktestRunResponse(run=service.serialize_run(run))


@router.get("/{run_id}", response_model=BacktestRunResponse)
def get_backtest_run(run_id: uuid.UUID, session: Session = Depends(get_db)) -> BacktestRunResponse:
    service = BacktestService(session)
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"BacktestRun {run_id} not found")
    return BacktestRunResponse(run=service.serialize_run(run))
