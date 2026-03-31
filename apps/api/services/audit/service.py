from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from db.models import AuditLog
from db.session import session_scope
from services.audit.contracts import AuditEvent


logger = logging.getLogger("ptr.audit")


def _clip(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


class AuditLogService:
    def write_event(self, event: AuditEvent) -> str:
        with session_scope() as session:
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
            session.add(record)
            session.flush()
            return str(record.id)

    def safe_write_event(self, event: AuditEvent, *, context: dict[str, Any] | None = None) -> str | None:
        try:
            return self.write_event(event)
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
