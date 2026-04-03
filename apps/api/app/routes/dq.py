from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from db.models import DataQualityResult, Market
from db.session import get_db


router = APIRouter(prefix="/dq", tags=["data-quality"])


class DQSummaryResponse(BaseModel):
    summary: dict[str, Any]
    recent_results: list[dict[str, Any]]


class DQDetailResponse(BaseModel):
    result: dict[str, Any]


@router.get("/summary", response_model=DQSummaryResponse)
def get_dq_summary(
    request: Request,
    session: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50, description="Number of recent results"),
) -> DQSummaryResponse:
    """Get DQ summary statistics."""
    # Get status distribution
    status_counts = dict(
        session.execute(
            select(DataQualityResult.status, func.count())
            .group_by(DataQualityResult.status)
        ).all()
    )

    # Get recent results
    recent = session.scalars(
        select(DataQualityResult)
        .order_by(desc(DataQualityResult.checked_at))
        .limit(limit)
    ).all()

    recent_data = [
        {
            "id": str(result.id),
            "market_ref_id": str(result.market_ref_id),
            "checked_at": result.checked_at.isoformat(),
            "status": result.status,
            "score": float(result.score) if result.score else None,
            "failure_count": result.failure_count,
            "rule_version": result.rule_version,
        }
        for result in recent
    ]

    summary = {
        "total_checks": sum(status_counts.values()),
        "status_distribution": status_counts,
        "pass_rate": status_counts.get("pass", 0) / sum(status_counts.values()) if status_counts else 0,
    }

    return DQSummaryResponse(
        summary=summary,
        recent_results=recent_data,
    )


@router.get("/markets/{market_id}", response_model=DQDetailResponse)
def get_market_dq_result(
    request: Request,
    market_id: str,
    session: Session = Depends(get_db),
) -> DQDetailResponse:
    """Get latest DQ result for a specific market."""
    # Find market
    market = session.scalar(
        select(Market).where(Market.market_id == market_id)
    )

    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # Get latest DQ result
    result = session.scalar(
        select(DataQualityResult)
        .where(DataQualityResult.market_ref_id == market.id)
        .order_by(desc(DataQualityResult.checked_at))
        .limit(1)
    )

    if not result:
        raise HTTPException(status_code=404, detail="No DQ result found for this market")

    result_data = {
        "id": str(result.id),
        "market_ref_id": str(result.market_ref_id),
        "checked_at": result.checked_at.isoformat(),
        "status": result.status,
        "score": float(result.score) if result.score else None,
        "failure_count": result.failure_count,
        "result_details": result.result_details,
        "rule_version": result.rule_version,
        "created_at": result.created_at.isoformat(),
    }

    return DQDetailResponse(result=result_data)
