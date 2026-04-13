from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from db.models import AuditLog
from db.session import session_scope
from services.audit.contracts import AuditEvent


logger = logging.getLogger("ptr.audit")

_SQLITE_LOCK_RETRY_DELAYS = (0.05, 0.1, 0.2)


def _clip(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


def _is_sqlite_locked_error(exc: Exception) -> bool:
    if not isinstance(exc, OperationalError):
        return False
    message = str(getattr(exc, "orig", exc)).lower()
    return "database is locked" in message or "database table is locked" in message


class AuditLogService:
    def _build_record_payload(self, event: AuditEvent) -> dict[str, Any]:
        return {
            "actor_id": _clip(event.actor_id, 128),
            "actor_type": _clip(event.actor_type, 64),
            "object_type": _clip(event.object_type, 64) or "unknown",
            "object_id": _clip(event.object_id, 128) or "unknown",
            "action": _clip(event.action, 64) or "unknown",
            "result": _clip(event.result, 32) or "unknown",
            "request_id": _clip(event.request_id, 128),
            "task_id": _clip(event.task_id, 128),
            "event_payload": event.event_payload,
        }

    def _log_extra(
        self,
        event: AuditEvent,
        *,
        context: dict[str, Any] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        payload = {
            "request_id": event.request_id or "-",
            "task_id": event.task_id or "-",
        }
        if context:
            payload.update(context)
        payload.update(extra)
        return payload

    def write_event(self, event: AuditEvent, session: Session | None = None) -> str:
        """
        Write audit event to database.

        Args:
            event: The audit event to write
            session: Optional existing session to use. If provided, the audit log
                    will be part of the same transaction as the caller's operations.
                    If None, creates a new session.
        """
        record_payload = self._build_record_payload(event)

        if session is not None:
            # Use provided session (same transaction as caller)
            record = AuditLog(**record_payload)
            session.add(record)
            session.flush()
            return str(record.id)

        # Create new session (independent transaction)
        with session_scope() as new_session:
            record = AuditLog(**record_payload)
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
        attempt = 0
        while True:
            try:
                return self.write_event(event, session=session)
            except Exception as exc:
                if session is None and _is_sqlite_locked_error(exc) and attempt < len(_SQLITE_LOCK_RETRY_DELAYS):
                    delay = _SQLITE_LOCK_RETRY_DELAYS[attempt]
                    attempt += 1
                    logger.warning(
                        "audit log write hit sqlite lock; retrying",
                        extra=self._log_extra(
                            event,
                            context=context,
                            retry_attempt=attempt,
                            retry_delay_ms=int(delay * 1000),
                        ),
                    )
                    time.sleep(delay)
                    continue

                logger.exception(
                    "audit log write failed",
                    extra=self._log_extra(
                        event,
                        context=context,
                        retry_attempt=attempt,
                    ),
                )
                return None


@lru_cache
def get_audit_log_service() -> AuditLogService:
    return AuditLogService()
