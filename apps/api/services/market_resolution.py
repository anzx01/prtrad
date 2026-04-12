from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def normalize_binary_resolution(value: Any) -> str | None:
    if value in (None, ""):
        return None

    normalized = str(value).strip().lower()
    if normalized in {"yes", "resolved_yes", "1", "true"}:
        return "yes"
    if normalized in {"no", "resolved_no", "0", "false"}:
        return "no"
    return None


def infer_binary_resolution_from_outcome_prices(outcome_prices: Any) -> str | None:
    parsed = outcome_prices
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            return None

    if not isinstance(parsed, list) or len(parsed) != 2:
        return None

    first_price = _decimal_or_none(parsed[0])
    second_price = _decimal_or_none(parsed[1])
    if first_price is None or second_price is None:
        return None

    if first_price == Decimal("1") and second_price == Decimal("0"):
        return "yes"
    if first_price == Decimal("0") and second_price == Decimal("1"):
        return "no"
    return None


def infer_binary_resolution_from_source_payload(source_payload: Any) -> str | None:
    if not isinstance(source_payload, dict):
        return None

    market_payload = source_payload.get("market")
    if not isinstance(market_payload, dict):
        return None

    return infer_binary_resolution_from_outcome_prices(market_payload.get("outcome_prices"))
