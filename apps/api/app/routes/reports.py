from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from services.reports import ReportService


router = APIRouter(prefix="/reports", tags=["reports"])


class ReportsResponse(BaseModel):
    reports: list[dict[str, Any]]


class AuditResponse(BaseModel):
    audit_events: list[dict[str, Any]]


class GenerateReportRequest(BaseModel):
    report_type: str
    generated_by: str | None = None
    days: int | None = Field(default=None, ge=1, le=90)
    stage_name: str | None = None


class GenerateReportResponse(BaseModel):
    report: dict[str, Any]


@router.get("", response_model=ReportsResponse)
def list_reports(
    report_type: str | None = None,
    session: Session = Depends(get_db),
) -> ReportsResponse:
    service = ReportService(db=session)
    reports = service.list_reports(report_type=report_type)
    return ReportsResponse(reports=reports)


@router.post("/generate", response_model=GenerateReportResponse)
def generate_report(
    body: GenerateReportRequest,
    session: Session = Depends(get_db),
) -> GenerateReportResponse:
    service = ReportService(db=session)
    try:
        report = service.generate_report(
            report_type=body.report_type,
            generated_by=body.generated_by,
            days=body.days,
            stage_name=body.stage_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session.commit()
    return GenerateReportResponse(report=service.serialize_report(report))


@router.get("/audit", response_model=AuditResponse)
def list_audit_events(limit: int = 50, session: Session = Depends(get_db)) -> AuditResponse:
    service = ReportService(db=session)
    return AuditResponse(audit_events=service.list_audit_events(limit=limit))
