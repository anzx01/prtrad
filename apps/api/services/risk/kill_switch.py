"""Kill-Switch 审批服务"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import KillSwitchRequest, RiskStateEvent

_TYPE_TO_STATE = {
    "freeze": "Frozen",
    "risk_off": "RiskOff",
    "unfreeze": "Normal",
}


class KillSwitchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def request_action(
        self,
        request_type: str,
        target_scope: str,
        requested_by: str,
        reason: str,
    ) -> KillSwitchRequest:
        req = KillSwitchRequest(
            id=uuid.uuid4(),
            request_type=request_type,
            target_scope=target_scope,
            requested_by=requested_by,
            reason=reason,
            status="pending",
        )
        self.db.add(req)
        self.db.flush()
        return req

    def approve(
        self,
        request_id: uuid.UUID,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> KillSwitchRequest:
        req = self._get_or_404(request_id)
        if req.status != "pending":
            raise ValueError(f"Request {request_id} is already {req.status}")

        req.status = "approved"
        req.reviewed_by = reviewer
        req.reviewed_at = datetime.now(UTC)
        req.review_notes = notes

        # 执行状态迁移
        from services.risk.service import RiskService
        risk_svc = RiskService(self.db)
        current = risk_svc.get_current_state()
        to_state = _TYPE_TO_STATE.get(req.request_type, "Normal")

        event = RiskStateEvent(
            id=uuid.uuid4(),
            from_state=current,
            to_state=to_state,
            trigger_type="manual",
            trigger_metric="kill_switch",
            trigger_value=0,
            threshold_value=0,
            actor_id=reviewer,
            notes=f"Kill-switch {req.request_type} approved by {reviewer}. Reason: {req.reason}",
        )
        self.db.add(event)
        self.db.flush()
        return req

    def reject(
        self,
        request_id: uuid.UUID,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> KillSwitchRequest:
        req = self._get_or_404(request_id)
        if req.status != "pending":
            raise ValueError(f"Request {request_id} is already {req.status}")

        req.status = "rejected"
        req.reviewed_by = reviewer
        req.reviewed_at = datetime.now(UTC)
        req.review_notes = notes
        self.db.flush()
        return req

    def list_requests(self, status: Optional[str] = None) -> list[KillSwitchRequest]:
        stmt = select(KillSwitchRequest).order_by(KillSwitchRequest.created_at.desc())
        if status:
            stmt = stmt.where(KillSwitchRequest.status == status)
        return list(self.db.scalars(stmt).all())

    def _get_or_404(self, request_id: uuid.UUID) -> KillSwitchRequest:
        req = self.db.scalar(select(KillSwitchRequest).where(KillSwitchRequest.id == request_id))
        if not req:
            raise ValueError(f"KillSwitchRequest {request_id} not found")
        return req
