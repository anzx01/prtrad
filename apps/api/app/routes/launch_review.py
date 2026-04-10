from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from services.launch_review import LaunchReviewService


router = APIRouter(prefix="/launch-review", tags=["launch-review"])


class LaunchReviewCreateRequest(BaseModel):
    title: str = ""
    stage_name: str = "M6"
    requested_by: str
    shadow_run_id: str | None = None
    checklist: list[dict[str, Any]] | None = None


class LaunchReviewDecisionRequest(BaseModel):
    decision: str
    reviewed_by: str
    notes: str | None = None


class LaunchReviewResponse(BaseModel):
    review: dict[str, Any]


class LaunchReviewListResponse(BaseModel):
    reviews: list[dict[str, Any]]


@router.get("", response_model=LaunchReviewListResponse)
def list_launch_reviews(limit: int = 20, session: Session = Depends(get_db)) -> LaunchReviewListResponse:
    service = LaunchReviewService(session)
    reviews = [service.serialize_review(review) for review in service.list_reviews(limit=limit)]
    return LaunchReviewListResponse(reviews=reviews)


@router.post("", response_model=LaunchReviewResponse)
def create_launch_review(
    body: LaunchReviewCreateRequest,
    session: Session = Depends(get_db),
) -> LaunchReviewResponse:
    service = LaunchReviewService(session)
    review = service.create_review(
        title=body.title,
        stage_name=body.stage_name,
        requested_by=body.requested_by,
        shadow_run_id=uuid.UUID(body.shadow_run_id) if body.shadow_run_id else None,
        checklist=body.checklist,
    )
    session.commit()
    return LaunchReviewResponse(review=service.serialize_review(review))


@router.post("/{review_id}/decide", response_model=LaunchReviewResponse)
def decide_launch_review(
    review_id: uuid.UUID,
    body: LaunchReviewDecisionRequest,
    session: Session = Depends(get_db),
) -> LaunchReviewResponse:
    service = LaunchReviewService(session)
    try:
        review = service.decide(
            review_id,
            decision=body.decision,
            reviewed_by=body.reviewed_by,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session.commit()
    return LaunchReviewResponse(review=service.serialize_review(review))


@router.get("/{review_id}", response_model=LaunchReviewResponse)
def get_launch_review(review_id: uuid.UUID, session: Session = Depends(get_db)) -> LaunchReviewResponse:
    service = LaunchReviewService(session)
    review = service.get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail=f"LaunchReview {review_id} not found")
    return LaunchReviewResponse(review=service.serialize_review(review))
