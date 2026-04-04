from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

class ReportsResponse(BaseModel):
    reports: list[dict[str, Any]]

@router.get("", response_model=ReportsResponse)
def list_reports(
    request: Request,
    session: Session = Depends(get_db),
) -> ReportsResponse:
    """List all reports."""
    service = ReportService(db=session)
    reports = service.list_reports()
    return ReportsResponse(reports=reports)
