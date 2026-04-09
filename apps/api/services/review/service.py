"""Review task service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from db.models import AuditLog, MarketClassificationResult, MarketReviewTask

from .contracts import ReviewTaskInput, ReviewTaskUpdate


REVIEW_STATUS_OPEN = "open"
REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_IN_PROGRESS = "in_progress"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"
REVIEW_STATUS_CANCELLED = "cancelled"

LEGACY_REVIEW_STATUS_ALIASES = {
    REVIEW_STATUS_OPEN: REVIEW_STATUS_PENDING,
}

ALLOWED_STATUS_TRANSITIONS = {
    REVIEW_STATUS_PENDING: [REVIEW_STATUS_IN_PROGRESS, REVIEW_STATUS_CANCELLED],
    REVIEW_STATUS_IN_PROGRESS: [REVIEW_STATUS_APPROVED, REVIEW_STATUS_REJECTED, REVIEW_STATUS_PENDING],
    REVIEW_STATUS_APPROVED: [],
    REVIEW_STATUS_REJECTED: [],
    REVIEW_STATUS_CANCELLED: [],
}


def _now_utc() -> datetime:
    return datetime.now(UTC)


def normalize_review_status(status: str | None) -> str | None:
    if status is None:
        return None
    return LEGACY_REVIEW_STATUS_ALIASES.get(status, status)


def review_statuses_for_filter(status: str | None) -> tuple[str, ...] | None:
    normalized = normalize_review_status(status)
    if normalized is None:
        return None
    if normalized == REVIEW_STATUS_PENDING:
        return (REVIEW_STATUS_PENDING, REVIEW_STATUS_OPEN)
    return (normalized,)


class ReviewService:
    """Core review task workflow service."""

    def __init__(
        self,
        db: Session,
        audit_service=None,
        task_id: str | None = None,
    ):
        self.db = db
        self.audit_service = audit_service
        self.task_id = task_id

    def create_review_task(self, review_input: ReviewTaskInput) -> MarketReviewTask:
        classification_result = self.db.get(MarketClassificationResult, review_input.classification_result_id)
        if not classification_result:
            raise ValueError(f"Classification result {review_input.classification_result_id} not found")

        existing_task = (
            self.db.execute(
                select(MarketReviewTask).where(
                    MarketReviewTask.classification_result_id == review_input.classification_result_id
                )
            )
            .scalars()
            .first()
        )
        if existing_task:
            raise ValueError(
                f"Review task already exists for classification result {review_input.classification_result_id}"
            )

        review_task = MarketReviewTask(
            market_ref_id=review_input.market_ref_id,
            classification_result_id=review_input.classification_result_id,
            queue_status=REVIEW_STATUS_PENDING,
            review_reason_code=review_input.review_reason_code,
            priority=review_input.priority,
            review_payload=review_input.review_payload or {},
        )

        self.db.add(review_task)
        self.db.flush()

        self._write_audit_log(
            object_id=str(review_task.id),
            action="create_review_task",
            result="success",
            payload={
                "market_ref_id": str(review_input.market_ref_id),
                "classification_result_id": str(review_input.classification_result_id),
                "review_reason_code": review_input.review_reason_code,
                "priority": review_input.priority,
            },
        )

        return review_task

    def get_review_queue(
        self,
        queue_status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketReviewTask]:
        query = select(MarketReviewTask).options(
            selectinload(MarketReviewTask.market),
            selectinload(MarketReviewTask.classification_result),
        )

        status_filters = review_statuses_for_filter(queue_status)
        if status_filters:
            if len(status_filters) == 1:
                query = query.where(MarketReviewTask.queue_status == status_filters[0])
            else:
                query = query.where(MarketReviewTask.queue_status.in_(status_filters))
        if priority:
            query = query.where(MarketReviewTask.priority == priority)
        if assigned_to:
            query = query.where(MarketReviewTask.assigned_to == assigned_to)

        priority_order = case(
            {"urgent": 1, "high": 2, "normal": 3, "low": 4},
            value=MarketReviewTask.priority,
            else_=5,
        )
        query = query.order_by(priority_order, MarketReviewTask.created_at.asc())

        query = query.limit(limit).offset(offset)
        return list(self.db.execute(query).scalars().all())

    def count_review_queue(
        self,
        queue_status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(MarketReviewTask)

        status_filters = review_statuses_for_filter(queue_status)
        if status_filters:
            if len(status_filters) == 1:
                query = query.where(MarketReviewTask.queue_status == status_filters[0])
            else:
                query = query.where(MarketReviewTask.queue_status.in_(status_filters))
        if priority:
            query = query.where(MarketReviewTask.priority == priority)
        if assigned_to:
            query = query.where(MarketReviewTask.assigned_to == assigned_to)

        return int(self.db.scalar(query) or 0)

    def update_review_task(
        self,
        review_task_id: UUID,
        update: ReviewTaskUpdate,
        actor_id: str | None = None,
    ) -> MarketReviewTask:
        review_task = self.db.get(MarketReviewTask, review_task_id)
        if not review_task:
            raise ValueError(f"Review task {review_task_id} not found")

        old_status = normalize_review_status(review_task.queue_status) or review_task.queue_status
        changes: dict[str, object] = {}

        next_status = normalize_review_status(update.queue_status)
        if next_status and next_status != old_status:
            if next_status not in ALLOWED_STATUS_TRANSITIONS.get(old_status, []):
                raise ValueError(f"Invalid status transition from {old_status} to {next_status}")
            review_task.queue_status = next_status
            changes["queue_status"] = {"from": old_status, "to": next_status}

            if next_status in [REVIEW_STATUS_APPROVED, REVIEW_STATUS_REJECTED, REVIEW_STATUS_CANCELLED]:
                review_task.resolved_at = _now_utc()
                changes["resolved_at"] = str(review_task.resolved_at)

        if update.assigned_to is not None:
            old_assigned = review_task.assigned_to
            review_task.assigned_to = update.assigned_to
            changes["assigned_to"] = {"from": old_assigned, "to": update.assigned_to}

        if update.review_payload is not None:
            review_task.review_payload = {
                **(review_task.review_payload or {}),
                **update.review_payload,
            }
            changes["review_payload_updated"] = True

        self.db.flush()

        self._write_audit_log(
            object_id=str(review_task_id),
            action="update_review_task",
            result="success",
            payload={
                "actor_id": actor_id,
                "changes": changes,
            },
        )

        return review_task

    def approve_review(
        self,
        review_task_id: UUID,
        actor_id: str,
        approval_notes: str | None = None,
    ) -> MarketReviewTask:
        review_task = self.db.get(MarketReviewTask, review_task_id)
        if not review_task:
            raise ValueError(f"Review task {review_task_id} not found")

        current_status = normalize_review_status(review_task.queue_status)
        if current_status != REVIEW_STATUS_IN_PROGRESS:
            raise ValueError(
                f"Cannot approve task in status {current_status}. "
                f"Task must be in {REVIEW_STATUS_IN_PROGRESS} status."
            )

        review_task.queue_status = REVIEW_STATUS_APPROVED
        review_task.resolved_at = _now_utc()
        review_task.review_payload = {
            **(review_task.review_payload or {}),
            "approved_by": actor_id,
            "approved_at": str(review_task.resolved_at),
            "approval_notes": approval_notes,
        }

        self.db.flush()

        self._write_audit_log(
            object_id=str(review_task_id),
            action="approve_review",
            result="success",
            payload={
                "actor_id": actor_id,
                "market_ref_id": str(review_task.market_ref_id),
                "approval_notes": approval_notes,
            },
        )

        return review_task

    def reject_review(
        self,
        review_task_id: UUID,
        actor_id: str,
        rejection_reason: str,
        rejection_notes: str | None = None,
    ) -> MarketReviewTask:
        review_task = self.db.get(MarketReviewTask, review_task_id)
        if not review_task:
            raise ValueError(f"Review task {review_task_id} not found")

        current_status = normalize_review_status(review_task.queue_status)
        if current_status != REVIEW_STATUS_IN_PROGRESS:
            raise ValueError(
                f"Cannot reject task in status {current_status}. "
                f"Task must be in {REVIEW_STATUS_IN_PROGRESS} status."
            )

        review_task.queue_status = REVIEW_STATUS_REJECTED
        review_task.resolved_at = _now_utc()
        review_task.review_payload = {
            **(review_task.review_payload or {}),
            "rejected_by": actor_id,
            "rejected_at": str(review_task.resolved_at),
            "rejection_reason": rejection_reason,
            "rejection_notes": rejection_notes,
        }

        self.db.flush()

        self._write_audit_log(
            object_id=str(review_task_id),
            action="reject_review",
            result="success",
            payload={
                "actor_id": actor_id,
                "market_ref_id": str(review_task.market_ref_id),
                "rejection_reason": rejection_reason,
                "rejection_notes": rejection_notes,
            },
        )

        return review_task

    def get_review_task(self, review_task_id: UUID) -> MarketReviewTask | None:
        return self.db.execute(
            select(MarketReviewTask)
            .where(MarketReviewTask.id == review_task_id)
            .options(
                selectinload(MarketReviewTask.market),
                selectinload(MarketReviewTask.classification_result),
            )
        ).scalar_one_or_none()

    def _write_audit_log(
        self,
        object_id: str,
        action: str,
        result: str,
        payload: dict | None = None,
    ) -> None:
        if self.audit_service:
            self.audit_service.log(
                object_type="market_review_task",
                object_id=object_id,
                action=action,
                result=result,
                event_payload=payload,
                task_id=self.task_id,
            )
        else:
            audit_log = AuditLog(
                actor_id="system",
                actor_type="service",
                object_type="market_review_task",
                object_id=object_id,
                action=action,
                result=result,
                task_id=self.task_id,
                event_payload=payload or {},
            )
            self.db.add(audit_log)
