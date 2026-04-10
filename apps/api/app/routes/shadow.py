from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from services.shadow import ShadowRunService


router = APIRouter(prefix="/shadow", tags=["shadow"])


class ShadowRunRequest(BaseModel):
    run_name: str = ""
    executed_by: str | None = None


class ShadowRunResponse(BaseModel):
    run: dict[str, Any]


class ShadowRunListResponse(BaseModel):
    runs: list[dict[str, Any]]


@router.get("", response_model=ShadowRunListResponse)
def list_shadow_runs(limit: int = 20, session: Session = Depends(get_db)) -> ShadowRunListResponse:
    service = ShadowRunService(session)
    runs = [service.serialize_run(run) for run in service.list_runs(limit=limit)]
    return ShadowRunListResponse(runs=runs)


@router.post("/execute", response_model=ShadowRunResponse)
def execute_shadow_run(
    body: ShadowRunRequest,
    session: Session = Depends(get_db),
) -> ShadowRunResponse:
    service = ShadowRunService(session)
    run = service.execute(run_name=body.run_name, executed_by=body.executed_by)
    session.commit()
    return ShadowRunResponse(run=service.serialize_run(run))


@router.get("/{run_id}", response_model=ShadowRunResponse)
def get_shadow_run(run_id: uuid.UUID, session: Session = Depends(get_db)) -> ShadowRunResponse:
    service = ShadowRunService(session)
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"ShadowRun {run_id} not found")
    return ShadowRunResponse(run=service.serialize_run(run))
