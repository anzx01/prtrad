from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AuditEvent:
    object_type: str
    object_id: str
    action: str
    result: str
    actor_id: str | None = None
    actor_type: str | None = None
    request_id: str | None = None
    task_id: str | None = None
    event_payload: dict[str, Any] | list[Any] | None = None
