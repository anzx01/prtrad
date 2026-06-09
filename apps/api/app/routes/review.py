from __future__ import annotations

from typing import Any, Literal
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


class BulkReviewActionResponse(BaseModel):
    tasks: list[dict[str, Any]]
    updated_count: int


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
    rejection_reason: str | None = Field(None, description="Rejection reason code")
    rejection_notes: str | None = Field(None, description="Rejection notes")


class BulkReviewActionRequest(BaseModel):
    task_ids: list[str] = Field(..., min_length=1, description="Review task UUIDs")
    action: Literal["start_review", "approve", "reject"] = Field(..., description="Bulk action type")
    actor_id: str = Field(..., description="Reviewer ID")
    rejection_reason: str | None = Field(None, description="Rejection reason code for bulk reject")
    notes: str | None = Field(None, description="Shared notes")


def _serialize_classification_result_summary(task: Any) -> dict[str, Any] | None:
    classification_result = getattr(task, "classification_result", None)
    if classification_result is None:
        return None
    return {
        "id": str(classification_result.id),
        "classification_status": classification_result.classification_status,
        "primary_category_code": classification_result.primary_category_code,
        "confidence": (
            float(classification_result.confidence)
            if classification_result.confidence is not None
            else None
        ),
        "requires_review": classification_result.requires_review,
        "conflict_count": classification_result.conflict_count,
    }


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _approval_block_reason_from_task(task: Any) -> str | None:
    classification_result = getattr(task, "classification_result", None)
    if classification_result is None:
        return "当前审核任务缺少正式分类结果，不能直接批准。"
    if not classification_result.primary_category_code:
        return "当前审核任务缺少正式主类别，不能直接批准。"
    if (
        classification_result.classification_status == "Blocked"
        or getattr(classification_result, "admission_bucket_code", None) == "LIST_BLACK"
    ):
        return "当前审核任务已命中阻断规则，应拒绝或自动拦截，不能批准。"
    return None


def _auto_reject_reason_code_from_task(task: Any) -> str | None:
    if _approval_block_reason_from_task(task) is None:
        return None

    classification_result = getattr(task, "classification_result", None)
    if classification_result is not None:
        if failure_reason_code := _normalize_optional_text(
            getattr(classification_result, "failure_reason_code", None)
        ):
            return failure_reason_code
        if (
            classification_result.classification_status == "Blocked"
            or getattr(classification_result, "admission_bucket_code", None) == "LIST_BLACK"
        ):
            return "TAG_BLACKLIST_MATCH"
        if not classification_result.primary_category_code:
            return "TAG_NO_CATEGORY_MATCH"

    if review_reason_code := _normalize_optional_text(getattr(task, "review_reason_code", None)):
        return review_reason_code

    return "TAG_MANUAL_REVIEW"


def _system_guidance_from_task(task: Any) -> dict[str, str]:
    queue_status = normalize_review_status(getattr(task, "queue_status", None)) or "pending"
    classification_result = getattr(task, "classification_result", None)
    approval_block_reason = _approval_block_reason_from_task(task)

    if queue_status == "approved":
        return {
            "system_conclusion_code": "ALREADY_APPROVED",
            "system_conclusion": "这条任务已处理完成",
            "system_reason": "这条任务已经批准，无需再继续处理。",
            "system_next_action": "view_only",
            "system_next_action_label": "查看结果",
        }
    if queue_status == "rejected":
        return {
            "system_conclusion_code": "ALREADY_REJECTED",
            "system_conclusion": "这条任务已退回",
            "system_reason": "这条任务已经退回，无需再继续处理。",
            "system_next_action": "view_only",
            "system_next_action_label": "查看结果",
        }
    if queue_status == "cancelled":
        return {
            "system_conclusion_code": "ALREADY_CANCELLED",
            "system_conclusion": "这条任务已被系统关闭",
            "system_reason": "这条任务已经被系统取消或关闭，无需再继续处理。",
            "system_next_action": "view_only",
            "system_next_action_label": "查看结果",
        }
    if approval_block_reason is None:
        return {
            "system_conclusion_code": "APPROVE_READY",
            "system_conclusion": "系统已形成可采纳结论",
            "system_reason": "正式主类别已经产出；核对市场信息无误后，通常可以直接批准。",
            "system_next_action": "approve",
            "system_next_action_label": "直接批准",
        }
    if classification_result is None:
        return {
            "system_conclusion_code": "CLASSIFICATION_RESULT_MISSING",
            "system_conclusion": "系统还没有拿到正式分类结果",
            "system_reason": "当前缺少正式分类结果，这类任务不应直接批准，更适合退回或等待重分类。",
            "system_next_action": "reject",
            "system_next_action_label": "直接退回",
        }
    if (
        classification_result.classification_status == "Blocked"
        or getattr(classification_result, "admission_bucket_code", None) == "LIST_BLACK"
    ):
        return {
            "system_conclusion_code": "AUTO_BLOCKED",
            "system_conclusion": "系统已判断这条不应放行",
            "system_reason": "这条任务命中了阻断规则，应直接退回或自动拦截，不建议人工放行。",
            "system_next_action": "reject",
            "system_next_action_label": "直接退回",
        }
    return {
        "system_conclusion_code": "PRIMARY_CATEGORY_MISSING",
        "system_conclusion": "系统还没有形成可采纳主类别",
        "system_reason": "主类别仍为空，说明自动分类还没有形成可接受结论，这类任务不应直接批准。",
        "system_next_action": "reject",
        "system_next_action_label": "直接退回",
    }


def _serialize_task_summary(task: Any) -> dict[str, Any]:
    approval_block_reason = _approval_block_reason_from_task(task)
    auto_reject_reason_code = _auto_reject_reason_code_from_task(task)
    system_guidance = _system_guidance_from_task(task)
    return {
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
        "classification_result": _serialize_classification_result_summary(task),
        "can_approve": approval_block_reason is None,
        "approval_block_reason": approval_block_reason,
        "auto_reject_reason_code": auto_reject_reason_code,
        **system_guidance,
        "market": {
            "market_id": task.market.market_id,
            "question": task.market.question,
        } if getattr(task, "market", None) else None,
    }


def _serialize_task_detail(task: Any) -> dict[str, Any]:
    task_data = _serialize_task_summary(task)
    task_data["market"] = {
        "id": str(task.market.id),
        "market_id": task.market.market_id,
        "question": task.market.question,
        "description": task.market.description,
        "market_status": task.market.market_status,
    } if task.market else None
    return task_data


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
    task_data = [_serialize_task_summary(task) for task in tasks]

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

    return ReviewTaskDetailResponse(task=_serialize_task_detail(task))


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

    return ReviewTaskDetailResponse(task=_serialize_task_summary(task))


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

    return ReviewTaskDetailResponse(task=_serialize_task_summary(task))


@router.post("/bulk-action", response_model=BulkReviewActionResponse)
def bulk_review_action(
    request: Request,
    body: BulkReviewActionRequest,
    session: Session = Depends(get_db),
) -> BulkReviewActionResponse:
    """Apply one review action to multiple tasks."""
    try:
        task_ids = [UUID(task_id) for task_id in body.task_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    review_service = ReviewService(db=session)

    try:
        tasks = review_service.bulk_apply_action(
            review_task_ids=task_ids,
            action=body.action,
            actor_id=body.actor_id,
            rejection_reason=body.rejection_reason,
            notes=body.notes,
        )
        session.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BulkReviewActionResponse(
        tasks=[_serialize_task_summary(task) for task in tasks],
        updated_count=len(tasks),
    )


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

    return ReviewTaskDetailResponse(task=_serialize_task_summary(task))


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

    return ReviewTaskDetailResponse(task=_serialize_task_summary(task))
