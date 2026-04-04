from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from services.reason_codes import ReasonCodeService


router = APIRouter(prefix="/reason-codes", tags=["reason-codes"])


class ReasonCodeListResponse(BaseModel):
    codes: list[dict[str, Any]]
    total: int


class ReasonCodeDetailResponse(BaseModel):
    code: dict[str, Any]


@router.get("", response_model=ReasonCodeListResponse)
def list_reason_codes(
    request: Request,
    session: Session = Depends(get_db),
    category: str | None = Query(None, description="Filter by category"),
    include_inactive: bool = Query(False, description="Include inactive codes"),
) -> ReasonCodeListResponse:
    """List all reason codes."""
    service = ReasonCodeService(db=session)
    codes = service.list_reason_codes(category=category, include_inactive=include_inactive)

    code_data = [
        {
            "id": str(code.id),
            "reason_code": code.reason_code,
            "reason_name": code.reason_name,
            "reason_category": code.reason_category,
            "description": code.description,
            "severity": code.severity,
            "is_active": code.is_active,
            "sort_order": code.sort_order,
            "created_at": code.created_at.isoformat(),
            "updated_at": code.updated_at.isoformat(),
        }
        for code in codes
    ]

    return ReasonCodeListResponse(codes=code_data, total=len(code_data))


@router.get("/{reason_code}", response_model=ReasonCodeDetailResponse)
def get_reason_code(
    request: Request,
    reason_code: str,
    session: Session = Depends(get_db),
) -> ReasonCodeDetailResponse:
    """Get a specific reason code."""
    service = ReasonCodeService(db=session)
    code = service.get_reason_code(reason_code)

    if not code:
        raise HTTPException(status_code=404, detail=f"Reason code {reason_code} not found")

    code_data = {
        "id": str(code.id),
        "reason_code": code.reason_code,
        "reason_name": code.reason_name,
        "reason_category": code.reason_category,
        "description": code.description,
        "severity": code.severity,
        "is_active": code.is_active,
        "sort_order": code.sort_order,
        "created_at": code.created_at.isoformat(),
        "updated_at": code.updated_at.isoformat(),
    }

    return ReasonCodeDetailResponse(code=code_data)
