from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DQCheckResult:
    code: str
    status: str
    severity: str
    message: str
    blocking: bool
    reason_code: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
