from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


ZERO = Decimal("0")
ONE = Decimal("1")
DECIMAL_6 = Decimal("0.000001")


@dataclass(frozen=True)
class BucketKey:
    category_code: str
    price_bucket: str
    time_bucket: str
    liquidity_tier: str
    window_type: str


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def quantize_6(value: Decimal) -> Decimal:
    return value.quantize(DECIMAL_6, rounding=ROUND_HALF_UP)


def clamp_probability(value: Decimal) -> Decimal:
    if value < ZERO:
        return ZERO
    if value > ONE:
        return ONE
    return value


def normalize_category(value: str | None) -> str:
    cleaned = (value or "").strip()
    return cleaned or "Uncategorized"


def midpoint_from_snapshot(snapshot: Any) -> Decimal | None:
    bid_yes = decimal_or_none(getattr(snapshot, "best_bid_yes", None))
    ask_yes = decimal_or_none(getattr(snapshot, "best_ask_yes", None))

    if bid_yes is not None and ask_yes is not None:
        return quantize_6(clamp_probability((bid_yes + ask_yes) / Decimal("2")))
    if bid_yes is not None:
        return quantize_6(clamp_probability(bid_yes))
    if ask_yes is not None:
        return quantize_6(clamp_probability(ask_yes))

    last_trade_no = decimal_or_none(getattr(snapshot, "last_trade_price_no", None))
    if last_trade_no is not None:
        return quantize_6(clamp_probability(ONE - last_trade_no))

    return None


def price_bucket_from_probability(probability: Decimal) -> str:
    value = clamp_probability(probability)

    if value < Decimal("0.10"):
        return "p00_10"
    if value < Decimal("0.30"):
        return "p10_30"
    if value < Decimal("0.50"):
        return "p30_50"
    if value < Decimal("0.70"):
        return "p50_70"
    if value < Decimal("0.90"):
        return "p70_90"
    return "p90_100"


def time_bucket_from_market(market: Any, reference_time: datetime | None = None) -> str:
    start = getattr(market, "open_time", None) or getattr(market, "creation_time", None) or reference_time
    end = getattr(market, "close_time", None) or getattr(market, "resolution_time", None) or reference_time

    if start is None or end is None:
        return "unknown"

    horizon_hours = max((end - start).total_seconds(), 0) / 3600
    if horizon_hours <= 24:
        return "lt_1d"
    if horizon_hours <= 72:
        return "d1_3"
    if horizon_hours <= 168:
        return "d3_7"
    return "gt_7d"


def liquidity_tier_from_snapshot(snapshot: Any) -> str:
    depth = decimal_or_none(getattr(snapshot, "cumulative_depth_at_target_size", None))
    if depth is None:
        depth = decimal_or_none(getattr(snapshot, "top_of_book_depth", None))
    volume = decimal_or_none(getattr(snapshot, "traded_volume", None))

    liquidity_signal = max(depth or ZERO, volume or ZERO)
    if liquidity_signal >= Decimal("10000"):
        return "deep"
    if liquidity_signal >= Decimal("1000"):
        return "standard"
    return "thin"


def outcome_from_resolution(final_resolution: str | None) -> Decimal | None:
    if final_resolution is None:
        return None

    normalized = final_resolution.strip().lower()
    if normalized in {"yes", "resolved_yes", "1", "true"}:
        return ONE
    if normalized in {"no", "resolved_no", "0", "false"}:
        return ZERO
    return None


def utc_now() -> datetime:
    return datetime.now(UTC)
