"""
审核任务服务

实现审核任务流的核心逻辑：
1. 创建审核任务
2. 查询审核队列
3. 更新审核状态
4. 审核决策（通过/拒绝）
5. 审核任务状态迁移
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from db.models import (
    AuditLog,
    Market,
    MarketClassificationResult,
    MarketReviewTask,
)

from .contracts import ReviewTaskInput, ReviewTaskUpdate


# 审核任务状态定义
REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_IN_PROGRESS = "in_progress"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"
REVIEW_STATUS_CANCELLED = "cancelled"

# 允许的状态迁移
ALLOWED_STATUS_TRANSITIONS = {
    REVIEW_STATUS_PENDING: [REVIEW_STATUS_IN_PROGRESS, REVIEW_STATUS_CANCELLED],
    REVIEW_STATUS_IN_PROGRESS: [REVIEW_STATUS_APPROVED, REVIEW_STATUS_REJECTED, REVIEW_STATUS_PENDING],
    REVIEW_STATUS_APPROVED: [],  # 终态
    REVIEW_STATUS_REJECTED: [],  # 终态
    REVIEW_STATUS_CANCELLED: [],  # 终态
}


def _now_utc() -> datetime:
    return datetime.now(UTC)


class ReviewService:
    """审核任务服务"""

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
        """
        创建审核任务

        Args:
            review_input: 审核任务输入

        Returns:
            MarketReviewTask: 创建的审核任务

        Raises:
            ValueError: 如果分类结果不存在或已有审核任务
        """
        # 验证分类结果存在
        classification_result = self.db.get(MarketClassificationResult, review_input.classification_result_id)
        if not classification_result:
            raise ValueError(f"Classification result {review_input.classification_result_id} not found")

        # 检查是否已存在审核任务
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

        # 创建审核任务
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

        # 写入审计日志
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
        """
        查询审核队列

        Args:
            queue_status: 队列状态过滤
            priority: 优先级过滤
            assigned_to: 分配人过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            list[MarketReviewTask]: 审核任务列表
        """
        query = select(MarketReviewTask).options(
            selectinload(MarketReviewTask.market),
            selectinload(MarketReviewTask.classification_result),
        )

        if queue_status:
            query = query.where(MarketReviewTask.queue_status == queue_status)
        if priority:
            query = query.where(MarketReviewTask.priority == priority)
        if assigned_to:
            query = query.where(MarketReviewTask.assigned_to == assigned_to)

        # 按优先级和创建时间排序
        from sqlalchemy import case
        priority_order = case(
            {"urgent": 1, "high": 2, "normal": 3, "low": 4},
            value=MarketReviewTask.priority,
            else_=5,
        )
        query = query.order_by(priority_order, MarketReviewTask.created_at.asc())

        query = query.limit(limit).offset(offset)

        return list(self.db.execute(query).scalars().all())

    def update_review_task(
        self,
        review_task_id: UUID,
        update: ReviewTaskUpdate,
        actor_id: str | None = None,
    ) -> MarketReviewTask:
        """
        更新审核任务

        Args:
            review_task_id: 审核任务 ID
            update: 更新数据
            actor_id: 操作者 ID

        Returns:
            MarketReviewTask: 更新后的审核任务

        Raises:
            ValueError: 如果任务不存在或状态迁移不合法
        """
        review_task = self.db.get(MarketReviewTask, review_task_id)
        if not review_task:
            raise ValueError(f"Review task {review_task_id} not found")

        old_status = review_task.queue_status
        changes = {}

        # 验证状态迁移
        if update.queue_status and update.queue_status != old_status:
            if update.queue_status not in ALLOWED_STATUS_TRANSITIONS.get(old_status, []):
                raise ValueError(
                    f"Invalid status transition from {old_status} to {update.queue_status}"
                )
            review_task.queue_status = update.queue_status
            changes["queue_status"] = {"from": old_status, "to": update.queue_status}

            # 如果是终态，记录解决时间
            if update.queue_status in [REVIEW_STATUS_APPROVED, REVIEW_STATUS_REJECTED, REVIEW_STATUS_CANCELLED]:
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

        # 写入审计日志
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
        """
        批准审核任务

        Args:
            review_task_id: 审核任务 ID
            actor_id: 审核人 ID
            approval_notes: 批准备注

        Returns:
            MarketReviewTask: 更新后的审核任务
        """
        review_task = self.db.get(MarketReviewTask, review_task_id)
        if not review_task:
            raise ValueError(f"Review task {review_task_id} not found")

        if review_task.queue_status != REVIEW_STATUS_IN_PROGRESS:
            raise ValueError(
                f"Cannot approve task in status {review_task.queue_status}. "
                f"Task must be in {REVIEW_STATUS_IN_PROGRESS} status."
            )

        # 更新任务状态
        review_task.queue_status = REVIEW_STATUS_APPROVED
        review_task.resolved_at = _now_utc()
        review_task.review_payload = {
            **(review_task.review_payload or {}),
            "approved_by": actor_id,
            "approved_at": str(review_task.resolved_at),
            "approval_notes": approval_notes,
        }

        self.db.flush()

        # 写入审计日志
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
        """
        拒绝审核任务

        Args:
            review_task_id: 审核任务 ID
            actor_id: 审核人 ID
            rejection_reason: 拒绝原因码
            rejection_notes: 拒绝备注

        Returns:
            MarketReviewTask: 更新后的审核任务
        """
        review_task = self.db.get(MarketReviewTask, review_task_id)
        if not review_task:
            raise ValueError(f"Review task {review_task_id} not found")

        if review_task.queue_status != REVIEW_STATUS_IN_PROGRESS:
            raise ValueError(
                f"Cannot reject task in status {review_task.queue_status}. "
                f"Task must be in {REVIEW_STATUS_IN_PROGRESS} status."
            )

        # 更新任务状态
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

        # 写入审计日志
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
        """
        获取单个审核任务

        Args:
            review_task_id: 审核任务 ID

        Returns:
            MarketReviewTask | None: 审核任务或 None
        """
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
        """写入审计日志"""
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
            # 直接写入数据库
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
