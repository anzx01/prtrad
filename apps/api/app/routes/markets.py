from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from db.models import DataQualityResult, Market, MarketSnapshot
from db.session import get_db


router = APIRouter(prefix="/markets", tags=["markets"])


class MarketListResponse(BaseModel):
    markets: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_more: bool


class MarketDetailResponse(BaseModel):
    market: dict[str, Any]
    latest_snapshot: dict[str, Any] | None
    latest_dq_result: dict[str, Any] | None


@router.get("", response_model=MarketListResponse)
def list_markets(
    request: Request,
    session: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by market status"),
    category: str | None = Query(None, description="Filter by category"),
    dq_status: str | None = Query(None, description="Filter by DQ status (pass/warn/fail)"),
    search: str | None = Query(None, description="Search in question"),
) -> MarketListResponse:
    """List markets with filtering and pagination."""
    stmt = select(Market).order_by(desc(Market.source_updated_at), desc(Market.updated_at))

    # Apply filters
    if status:
        stmt = stmt.where(Market.market_status == status)
    if category:
        stmt = stmt.where(Market.category_raw.ilike(f"%{category}%"))
    if search:
        stmt = stmt.where(Market.question.ilike(f"%{search}%"))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.scalar(count_stmt) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size + 1)

    markets = session.scalars(stmt).all()
    has_more = len(markets) > page_size
    if has_more:
        markets = markets[:page_size]

    # Serialize markets
    market_data = [
        {
            "id": str(market.id),
            "market_id": market.market_id,
            "question": market.question,
            "description": market.description,
            "market_status": market.market_status,
            "category_raw": market.category_raw,
            "close_time": market.close_time.isoformat() if market.close_time else None,
            "created_at": market.created_at.isoformat(),
            "updated_at": market.updated_at.isoformat(),
        }
        for market in markets
    ]

    return MarketListResponse(
        markets=market_data,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/{market_id}", response_model=MarketDetailResponse)
def get_market_detail(
    request: Request,
    market_id: str,
    session: Session = Depends(get_db),
) -> MarketDetailResponse:
    """Get market detail with latest snapshot and DQ result."""
    # Load market
    market = session.scalar(
        select(Market)
        .where(Market.market_id == market_id)
    )

    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # Get latest snapshot
    latest_snapshot = session.scalar(
        select(MarketSnapshot)
        .where(MarketSnapshot.market_ref_id == market.id)
        .order_by(desc(MarketSnapshot.snapshot_time))
        .limit(1)
    )

    # Get latest DQ result
    latest_dq = session.scalar(
        select(DataQualityResult)
        .where(DataQualityResult.market_ref_id == market.id)
        .order_by(desc(DataQualityResult.checked_at))
        .limit(1)
    )

    # Serialize market
    market_data = {
        "id": str(market.id),
        "market_id": market.market_id,
        "event_id": market.event_id,
        "condition_id": market.condition_id,
        "question": market.question,
        "description": market.description,
        "resolution_criteria": market.resolution_criteria,
        "creation_time": market.creation_time.isoformat() if market.creation_time else None,
        "open_time": market.open_time.isoformat() if market.open_time else None,
        "close_time": market.close_time.isoformat() if market.close_time else None,
        "resolution_time": market.resolution_time.isoformat() if market.resolution_time else None,
        "final_resolution": market.final_resolution,
        "market_status": market.market_status,
        "category_raw": market.category_raw,
        "related_tags": market.related_tags,
        "outcomes": market.outcomes,
        "clob_token_ids": market.clob_token_ids,
        "source_updated_at": market.source_updated_at.isoformat() if market.source_updated_at else None,
        "created_at": market.created_at.isoformat(),
        "updated_at": market.updated_at.isoformat(),
    }

    # Serialize snapshot
    snapshot_data = None
    if latest_snapshot:
        snapshot_data = {
            "snapshot_time": latest_snapshot.snapshot_time.isoformat(),
            "best_bid_no": float(latest_snapshot.best_bid_no) if latest_snapshot.best_bid_no else None,
            "best_ask_no": float(latest_snapshot.best_ask_no) if latest_snapshot.best_ask_no else None,
            "spread": float(latest_snapshot.spread) if latest_snapshot.spread else None,
            "top_of_book_depth": float(latest_snapshot.top_of_book_depth) if latest_snapshot.top_of_book_depth else None,
            "traded_volume": float(latest_snapshot.traded_volume) if latest_snapshot.traded_volume else None,
        }

    # Serialize DQ result
    dq_data = None
    if latest_dq:
        dq_data = {
            "checked_at": latest_dq.checked_at.isoformat(),
            "status": latest_dq.status,
            "score": float(latest_dq.score) if latest_dq.score else None,
            "failure_count": latest_dq.failure_count,
            "rule_version": latest_dq.rule_version,
            "result_details": latest_dq.result_details,
        }

    return MarketDetailResponse(
        market=market_data,
        latest_snapshot=snapshot_data,
        latest_dq_result=dq_data,
    )
