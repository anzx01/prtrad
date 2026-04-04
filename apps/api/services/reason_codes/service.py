"""
拒绝原因码服务
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import AuditLog, RejectionReasonCode, RejectionReasonStats

from .contracts import ReasonCodeInput, ReasonCodeUpdate


class ReasonCodeService:
    """拒绝原因码服务"""

    def __init__(self, db: Session, audit_service=None, task_id: str | None = None):
        self.db = db
        self.audit_service = audit_service
        self.task_id = task_id

    def create_reason_code(self, input_data: ReasonCodeInput) -> RejectionReasonCode:
        """创建原因码"""
        # 检查是否已存在
        existing = self.db.scalar(
            select(RejectionReasonCode).where(RejectionReasonCode.reason_code == input_data.reason_code)
        )
        if existing:
            raise ValueError(f"Reason code {input_data.reason_code} already exists")

        reason_code = RejectionReasonCode(
            reason_code=input_data.reason_code,
            reason_name=input_data.reason_name,
            reason_category=input_data.reason_category,
            description=input_data.description,
            severity=input_data.severity,
            sort_order=input_data.sort_order,
        )

        self.db.add(reason_code)
        self.db.flush()

        self._write_audit_log(
            object_id=str(reason_code.id),
            action="create_reason_code",
            result="success",
            payload={"reason_code": input_data.reason_code},
        )

        return reason_code

    def list_reason_codes(
        self, category: str | None = None, include_inactive: bool = False
    ) -> list[RejectionReasonCode]:
        """获取原因码列表"""
        query = select(RejectionReasonCode).order_by(
            RejectionReasonCode.reason_category, RejectionReasonCode.sort_order
        )

        if category:
            query = query.where(RejectionReasonCode.reason_category == category)
        if not include_inactive:
            query = query.where(RejectionReasonCode.is_active == True)  # noqa: E712

        return list(self.db.scalars(query).all())

    def get_reason_code(self, reason_code: str) -> RejectionReasonCode | None:
        """获取单个原因码"""
        return self.db.scalar(
            select(RejectionReasonCode).where(RejectionReasonCode.reason_code == reason_code)
        )

    def update_reason_code(self, reason_code: str, update: ReasonCodeUpdate) -> RejectionReasonCode:
        """更新原因码"""
        code = self.get_reason_code(reason_code)
        if not code:
            raise ValueError(f"Reason code {reason_code} not found")

        if update.reason_name is not None:
            code.reason_name = update.reason_name
        if update.description is not None:
            code.description = update.description
        if update.severity is not None:
            code.severity = update.severity
        if update.is_active is not None:
            code.is_active = update.is_active
        if update.sort_order is not None:
            code.sort_order = update.sort_order

        self.db.flush()

        self._write_audit_log(
            object_id=str(code.id),
            action="update_reason_code",
            result="success",
            payload={"reason_code": reason_code},
        )

        return code

    def _write_audit_log(self, object_id: str, action: str, result: str, payload: dict | None = None) -> None:
        """写入审计日志"""
        if self.audit_service:
            self.audit_service.log(
                object_type="rejection_reason_code",
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
                object_type="rejection_reason_code",
                object_id=object_id,
                action=action,
                result=result,
                task_id=self.task_id,
                event_payload=payload or {},
            )
            self.db.add(audit_log)
