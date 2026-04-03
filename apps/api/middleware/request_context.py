from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request
from starlette.responses import Response

from services.audit import AuditEvent, get_audit_log_service


logger = logging.getLogger("ptr.api.middleware")


def _validate_actor_id(actor_id: str | None) -> str | None:
    """
    Validate actor_id from request headers.

    TODO: Replace with proper JWT/session validation.
    For now, we accept the header value but log suspicious patterns.
    """
    if not actor_id:
        return None

    # Basic validation: check for suspicious patterns
    if len(actor_id) > 128:
        logger.warning(f"Suspicious actor_id length: {len(actor_id)}")
        return None

    # TODO: Add JWT validation here
    # TODO: Verify actor_id against user database
    # TODO: Check permissions and roles

    return actor_id


async def request_context_middleware(request: Request, call_next: Callable) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

    # Validate actor information
    actor_id = _validate_actor_id(request.headers.get("x-actor-id"))
    actor_type = request.headers.get("x-actor-type")

    # Log warning if actor_id is provided without validation
    if actor_id and not request.headers.get("authorization"):
        logger.warning(
            f"Actor ID provided without authorization header: {actor_id}",
            extra={"request_id": request_id}
        )

    request.state.request_id = request_id
    request.state.actor_id = actor_id
    request.state.actor_type = actor_type

    started_at = time.perf_counter()
    audit_service = get_audit_log_service()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                object_type="api_request",
                object_id=f"{request.method} {request.url.path}",
                action="request.exception",
                result="error",
                request_id=request_id,
                event_payload={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
        )
        raise

    response.headers["x-request-id"] = request_id
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

    # Improved status determination
    if response.status_code < 400:
        result = "success"
    elif response.status_code < 500:
        result = "client_error"
    else:
        result = "server_error"

    audit_service.safe_write_event(
        AuditEvent(
            actor_id=actor_id,
            actor_type=actor_type,
            object_type="api_request",
            object_id=f"{request.method} {request.url.path}",
            action="request.completed",
            result=result,
            request_id=request_id,
            event_payload={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
    )
    return response
