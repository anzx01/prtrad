from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ExecutionAdapterResult:
    status: str
    provider: str
    provider_order_id: str | None = None
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class CollateralBalanceSnapshot:
    balance: Decimal | None
    allowance: Decimal | None
    available: Decimal | None
    funder_address: str | None = None
    signature_type: int | None = None
    raw: dict[str, Any] | None = None


class ExecutionAdapterError(RuntimeError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
