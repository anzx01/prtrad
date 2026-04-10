"""Kill-switch approval workflow."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import KillSwitchRequest, RiskStateEvent
from services.audit import AuditEvent


_TYPE_TO_STATE = {
    "freeze": "Frozen",
    "risk_off": "RiskOff",
    "unfreeze": "Normal",
}


class KillSwitchService:
    def __init__(self, db: Session, audit_service=None) -> None:
        self.db = db
        if audit_service is None:
            from services.audit import get_audit_log_service

            audit_service = get_audit_log_service()
        self.audit_service = audit_service

    def request_action(
        self,
        request_type: str,
        target_scope: str,
        requested_by: str,
        reason: str,
    ) -> KillSwitchRequest:
        request = KillSwitchRequest(
            id=uuid.uuid4(),
            request_type=request_type,
            target_scope=target_scope,
            requested_by=requested_by,
            reason=reason,
            status="pending",
            created_at=datetime.now(UTC),
        )
        self.db.add(request)
        self.db.flush()
        self._write_audit(
            request=request,
            action="request",
            result="pending",
            actor_id=requested_by,
            payload={"target_scope": target_scope, "reason": reason},
        )
        return request

    def approve(
        self,
        request_id: uuid.UUID,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> KillSwitchRequest:
        request = self._get_or_404(request_id)
        if request.status != "pending":
            raise ValueError(f"Request {request_id} is already {request.status}")

        request.status = "approved"
        request.reviewed_by = reviewer
        request.reviewed_at = datetime.now(UTC)
        request.review_notes = notes

        from services.risk.service import RiskService

        risk_service = RiskService(self.db)
        current_state = risk_service.get_current_state()
        target_state = _TYPE_TO_STATE.get(request.request_type, "Normal")

        event = RiskStateEvent(
            id=uuid.uuid4(),
            from_state=current_state,
            to_state=target_state,
            trigger_type="manual",
            trigger_metric="kill_switch",
            trigger_value=0,
            threshold_value=0,
            actor_id=reviewer,
            notes=(
                f"Kill-switch {request.request_type} approved by {reviewer}. "
                f"Reason: {request.reason}"
            ),
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        self.db.flush()
        self._write_audit(
            request=request,
            action="approve",
            result="approved",
            actor_id=reviewer,
            payload={
                "target_scope": request.target_scope,
                "request_type": request.request_type,
                "notes": notes,
                "to_state": target_state,
            },
        )
        return request

    def reject(
        self,
        request_id: uuid.UUID,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> KillSwitchRequest:
        request = self._get_or_404(request_id)
        if request.status != "pending":
            raise ValueError(f"Request {request_id} is already {request.status}")

        request.status = "rejected"
        request.reviewed_by = reviewer
        request.reviewed_at = datetime.now(UTC)
        request.review_notes = notes
        self.db.flush()
        self._write_audit(
            request=request,
            action="reject",
            result="rejected",
            actor_id=reviewer,
            payload={
                "target_scope": request.target_scope,
                "request_type": request.request_type,
                "notes": notes,
            },
        )
        return request

    def list_requests(self, status: Optional[str] = None) -> list[KillSwitchRequest]:
        statement = select(KillSwitchRequest).order_by(KillSwitchRequest.created_at.desc())
        if status:
            statement = statement.where(KillSwitchRequest.status == status)
        return list(self.db.scalars(statement).all())

    def _get_or_404(self, request_id: uuid.UUID) -> KillSwitchRequest:
        request = self.db.scalar(
            select(KillSwitchRequest).where(KillSwitchRequest.id == request_id)
        )
        if not request:
            raise ValueError(f"KillSwitchRequest {request_id} not found")
        return request

    def _write_audit(
        self,
        *,
        request: KillSwitchRequest,
        action: str,
        result: str,
        actor_id: str | None,
        payload: dict,
    ) -> None:
        if self.audit_service is None:
            return
        self.audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type="user" if actor_id else "system",
                object_type="kill_switch_request",
                object_id=str(request.id),
                action=action,
                result=result,
                event_payload=payload,
            ),
            session=self.db,
        )
