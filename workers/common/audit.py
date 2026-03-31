from __future__ import annotations

from typing import Any

from services.audit import AuditEvent, get_audit_log_service


def record_worker_audit_event(
    *,
    object_type: str,
    object_id: str,
    action: str,
    result: str,
    task_id: str | None,
    actor_id: str | None,
    event_payload: dict[str, Any] | None = None,
) -> str | None:
    service = get_audit_log_service()
    return service.safe_write_event(
        AuditEvent(
            actor_id=actor_id,
            actor_type="system",
            object_type=object_type,
            object_id=object_id,
            action=action,
            result=result,
            task_id=task_id,
            event_payload=event_payload,
        )
    )


def record_worker_task_retry(
    *,
    task_id: str,
    task_name: str,
    reason: str,
    retry_count: int | None,
) -> str | None:
    return record_worker_audit_event(
        object_type="worker_task",
        object_id=task_id,
        action="retry_scheduled",
        result="retry",
        task_id=task_id,
        actor_id=task_name,
        event_payload={
            "task_name": task_name,
            "reason": reason,
            "retry_count": retry_count,
        },
    )


def record_worker_task_failure(
    *,
    task_id: str,
    task_name: str,
    reason: str,
    kwargs: dict[str, Any],
) -> str | None:
    return record_worker_audit_event(
        object_type="worker_task",
        object_id=task_id,
        action="execute",
        result="failed",
        task_id=task_id,
        actor_id=task_name,
        event_payload={
            "task_name": task_name,
            "reason": reason,
            "kwargs_keys": sorted(kwargs.keys()),
        },
    )
