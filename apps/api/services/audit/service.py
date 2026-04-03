from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from sqlalchemy.orm import Session

from db.models import AuditLog
from db.session import session_scope
from services.audit.contracts import AuditEvent


logger = logging.getLogger("ptr.audit")


def _clip(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


class AuditLogService:
    def write_event(self, event: AuditEvent, session: Session | None = None) -> str:
        """
        Write audit event to database.

        Args:
            event: The audit event to write
            session: Optional existing session to use. If provided, the audit log
                    will be part of the same transaction as the caller's operations.
                    If None, creates a new session.
        """
        record = AuditLog(
            actor_id=_clip(event.actor_id, 128),
            actor_type=_clip(event.actor_type, 64),
            object_type=_clip(event.object_type, 64) or "unknown",
            object_id=_clip(event.object_id, 128) or "unknown",
            action=_clip(event.action, 64) or "unknown",
            result=_clip(event.result, 32) or "unknown",
            request_id=_clip(event.request_id, 128),
            task_id=_clip(event.task_id, 128),
            event_payload=event.event_payload,
        )

        if session:
            # Use provided session (same transaction as caller)
            session.add(record)
            session.flush()
            return str(record.id)
        else:
            # Create new session (independent transaction)
            with session_scope() as new_session:
                new_session.add(record)
                new_session.flush()
                return str(record.id)

    def safe_write_event(
        self,
        event: AuditEvent,
        session: Session | None = None,
        *,
        context: dict[str, Any] | None = None
    ) -> str | None:
        """
        Safely write audit event, catching and logging any errors.

        Args:
            event: The audit event to write
            session: Optional existing session to use
            context: Optional context for error logging
        """
        try:
            return self.write_event(event, session=session)
        except Exception:
            logger.exception(
                "audit log write failed",
                extra={
                    "request_id": event.request_id or "-",
                    "task_id": event.task_id or "-",
                },
            )
            return None


@lru_cache
def get_audit_log_service() -> AuditLogService:
    return AuditLogService()
