from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from services.review import ReviewService, ReviewTaskInput, ReviewTaskUpdate
from services.review.service import normalize_review_status


router = APIRouter(prefix="/review", tags=["review"])


class ReviewQueueResponse(BaseModel):
    tasks: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class ReviewTaskDetailResponse(BaseModel):
    task: dict[str, Any]


class CreateReviewTaskRequest(BaseModel):
    market_ref_id: str = Field(..., description="Market UUID")
    classification_result_id: str = Field(..., description="Classification result UUID")
    review_reason_code: str | None = Field(None, description="Review reason code")
    priority: str = Field("normal", description="Priority: low, normal, high, urgent")
    review_payload: dict | None = Field(None, description="Additional review data")


class UpdateReviewTaskRequest(BaseModel):
    queue_status: str | None = Field(None, description="New queue status")
    assigned_to: str | None = Field(None, description="Assign to reviewer")
    review_payload: dict | None = Field(None, description="Additional review data")


class ApproveReviewRequest(BaseModel):
    actor_id: str = Field(..., description="Reviewer ID")
    approval_notes: str | None = Field(None, description="Approval notes")


class RejectReviewRequest(BaseModel):
    actor_id: str = Field(..., description="Reviewer ID")
    rejection_reason: str = Field(..., description="Rejection reason code")
    rejection_notes: str | None = Field(None, description="Rejection notes")


@router.get("/queue", response_model=ReviewQueueResponse)
def get_review_queue(
    request: Request,
    session: Session = Depends(get_db),
    queue_status: str | None = Query(None, description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    assigned_to: str | None = Query(None, description="Filter by assignee"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ReviewQueueResponse:
    """Get review queue with filtering and pagination."""
    review_service = ReviewService(db=session)

    offset = (page - 1) * page_size
    total = review_service.count_review_queue(
        queue_status=queue_status,
        priority=priority,
        assigned_to=assigned_to,
    )
    tasks = review_service.get_review_queue(
        queue_status=queue_status,
        priority=priority,
        assigned_to=assigned_to,
        limit=page_size,
        offset=offset,
    )

    # Serialize tasks
    task_data = [
        {
            "id": str(task.id),
            "market_ref_id": str(task.market_ref_id),
            "classification_result_id": str(task.classification_result_id),
            "queue_status": normalize_review_status(task.queue_status),
            "review_reason_code": task.review_reason_code,
            "priority": task.priority,
            "assigned_to": task.assigned_to,
            "review_payload": task.review_payload,
            "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "market": {
                "market_id": task.market.market_id,
                "question": task.market.question,
            } if task.market else None,
        }
        for task in tasks
    ]

    return ReviewQueueResponse(
        tasks=task_data,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=ReviewTaskDetailResponse)
def get_review_task(
    request: Request,
    task_id: str,
    session: Session = Depends(get_db),
) -> ReviewTaskDetailResponse:
    """Get review task detail."""
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    review_service = ReviewService(db=session)
    task = review_service.get_review_task(task_uuid)

    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")

    # Serialize task with full details
    task_data = {
        "id": str(task.id),
        "market_ref_id": str(task.market_ref_id),
        "classification_result_id": str(task.classification_result_id),
        "queue_status": normalize_review_status(task.queue_status),
        "review_reason_code": task.review_reason_code,
        "priority": task.priority,
        "assigned_to": task.assigned_to,
        "review_payload": task.review_payload,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "market": {
            "id": str(task.market.id),
            "market_id": task.market.market_id,
            "question": task.market.question,
            "description": task.market.description,
            "market_status": task.market.market_status,
        } if task.market else None,
        "classification_result": {
            "id": str(task.classification_result.id),
            "classification_status": task.classification_result.classification_status,
            "primary_category_code": task.classification_result.primary_category_code,
            "confidence": float(task.classification_result.confidence) if task.classification_result.confidence else None,
            "requires_review": task.classification_result.requires_review,
            "conflict_count": task.classification_result.conflict_count,
        } if task.classification_result else None,
    }

    return ReviewTaskDetailResponse(task=task_data)


@router.post("", response_model=ReviewTaskDetailResponse, status_code=201)
def create_review_task(
    request: Request,
    body: CreateReviewTaskRequest,
    session: Session = Depends(get_db),
) -> ReviewTaskDetailResponse:
    """Create a new review task."""
    try:
        market_ref_id = UUID(body.market_ref_id)
        classification_result_id = UUID(body.classification_result_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    review_service = ReviewService(db=session)

    review_input = ReviewTaskInput(
        market_ref_id=market_ref_id,
        classification_result_id=classification_result_id,
        review_reason_code=body.review_reason_code,
        priority=body.priority,
        review_payload=body.review_payload,
    )

    try:
        task = review_service.create_review_task(review_input)
        session.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_data = {
        "id": str(task.id),
        "market_ref_id": str(task.market_ref_id),
        "classification_result_id": str(task.classification_result_id),
        "queue_status": normalize_review_status(task.queue_status),
        "review_reason_code": task.review_reason_code,
        "priority": task.priority,
        "assigned_to": task.assigned_to,
        "review_payload": task.review_payload,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }

    return ReviewTaskDetailResponse(task=task_data)


@router.patch("/{task_id}", response_model=ReviewTaskDetailResponse)
def update_review_task(
    request: Request,
    task_id: str,
    body: UpdateReviewTaskRequest,
    session: Session = Depends(get_db),
    actor_id: str | None = Query(None, description="Actor ID for audit"),
) -> ReviewTaskDetailResponse:
    """Update review task."""
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    review_service = ReviewService(db=session)

    update = ReviewTaskUpdate(
        queue_status=body.queue_status,
        assigned_to=body.assigned_to,
        review_payload=body.review_payload,
    )

    try:
        task = review_service.update_review_task(
            review_task_id=task_uuid,
            update=update,
            actor_id=actor_id,
        )
        session.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_data = {
        "id": str(task.id),
        "market_ref_id": str(task.market_ref_id),
        "classification_result_id": str(task.classification_result_id),
        "queue_status": normalize_review_status(task.queue_status),
        "review_reason_code": task.review_reason_code,
        "priority": task.priority,
        "assigned_to": task.assigned_to,
        "review_payload": task.review_payload,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }

    return ReviewTaskDetailResponse(task=task_data)


@router.post("/{task_id}/approve", response_model=ReviewTaskDetailResponse)
def approve_review_task(
    request: Request,
    task_id: str,
    body: ApproveReviewRequest,
    session: Session = Depends(get_db),
) -> ReviewTaskDetailResponse:
    """Approve review task."""
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    review_service = ReviewService(db=session)

    try:
        task = review_service.approve_review(
            review_task_id=task_uuid,
            actor_id=body.actor_id,
            approval_notes=body.approval_notes,
        )
        session.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_data = {
        "id": str(task.id),
        "market_ref_id": str(task.market_ref_id),
        "classification_result_id": str(task.classification_result_id),
        "queue_status": normalize_review_status(task.queue_status),
        "review_reason_code": task.review_reason_code,
        "priority": task.priority,
        "assigned_to": task.assigned_to,
        "review_payload": task.review_payload,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }

    return ReviewTaskDetailResponse(task=task_data)


@router.post("/{task_id}/reject", response_model=ReviewTaskDetailResponse)
def reject_review_task(
    request: Request,
    task_id: str,
    body: RejectReviewRequest,
    session: Session = Depends(get_db),
) -> ReviewTaskDetailResponse:
    """Reject review task."""
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    review_service = ReviewService(db=session)

    try:
        task = review_service.reject_review(
            review_task_id=task_uuid,
            actor_id=body.actor_id,
            rejection_reason=body.rejection_reason,
            rejection_notes=body.rejection_notes,
        )
        session.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_data = {
        "id": str(task.id),
        "market_ref_id": str(task.market_ref_id),
        "classification_result_id": str(task.classification_result_id),
        "queue_status": normalize_review_status(task.queue_status),
        "review_reason_code": task.review_reason_code,
        "priority": task.priority,
        "assigned_to": task.assigned_to,
        "review_payload": task.review_payload,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }

    return ReviewTaskDetailResponse(task=task_data)
