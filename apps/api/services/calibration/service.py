"""M3 校准服务"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from db.models import CalibrationUnit, Market, MarketSnapshot
from services.market_resolution import (
    infer_binary_resolution_from_source_payload,
    normalize_binary_resolution,
)
from services.m3_helpers import (
    BucketKey,
    liquidity_tier_from_snapshot,
    midpoint_from_snapshot,
    normalize_category,
    outcome_from_resolution,
    price_bucket_from_probability,
    quantize_6,
    time_bucket_from_market,
    utc_now,
)


MIN_ACTIVE_SAMPLE_COUNT = 5
WINDOW_LOOKBACK_DAYS = {
    "short": 14,
    "long": 90,
}
DEFAULT_LOOKBACK_DAYS = 90


@dataclass(frozen=True)
class AggregatedCalibrationStats:
    sample_count: int
    edge_estimate: Decimal
    interval_low: Decimal
    interval_high: Decimal
    is_active: bool
    disabled_reason: str | None


class CalibrationService:
    def __init__(self, db: Session):
        self.db = db

    def list_units(self, include_inactive: bool = False) -> list[CalibrationUnit]:
        stmt = select(CalibrationUnit)
        if not include_inactive:
            stmt = stmt.where(CalibrationUnit.is_active.is_(True))

        stmt = stmt.order_by(
            CalibrationUnit.category_code,
            CalibrationUnit.price_bucket,
            CalibrationUnit.time_bucket,
            CalibrationUnit.liquidity_tier,
            CalibrationUnit.window_type,
        )
        return list(self.db.scalars(stmt).all())

    def list_active_units(self) -> list[CalibrationUnit]:
        return self.list_units(include_inactive=False)

    def get_unit(self, unit_id: uuid.UUID) -> CalibrationUnit | None:
        return self.db.get(CalibrationUnit, unit_id)

    def compute_calibration(
        self,
        category_code: str,
        price_bucket: str,
        time_bucket: str,
        liquidity_tier: str = "standard",
        window_type: str = "long",
    ) -> CalibrationUnit:
        now = utc_now()
        key = BucketKey(
            category_code=normalize_category(category_code),
            price_bucket=price_bucket,
            time_bucket=time_bucket,
            liquidity_tier=liquidity_tier,
            window_type=window_type,
        )
        stats_by_key = self._collect_sample_stats(window_type=window_type)
        unit = self._upsert_unit(key=key, stats=stats_by_key.get(key), now=now)

        self.db.commit()
        self.db.refresh(unit)
        return unit

    def recompute_all(self, window_type: str = "long") -> list[CalibrationUnit]:
        now = utc_now()
        stats_by_key = self._collect_sample_stats(window_type=window_type)

        existing_units = list(
            self.db.scalars(
                select(CalibrationUnit).where(CalibrationUnit.window_type == window_type)
            ).all()
        )
        existing_by_key = {self._unit_key(unit): unit for unit in existing_units}
        touched_keys: set[BucketKey] = set()

        for key, stats in stats_by_key.items():
            self._upsert_unit(key=key, stats=stats, now=now)
            touched_keys.add(key)

        for key, unit in existing_by_key.items():
            if key in touched_keys:
                continue
            unit.sample_count = 0
            unit.edge_estimate = Decimal("0")
            unit.interval_low = Decimal("0")
            unit.interval_high = Decimal("0")
            unit.is_active = False
            unit.disabled_reason = "no_historical_samples"
            unit.computed_at = now

        self.db.commit()
        return list(
            self.db.scalars(
                select(CalibrationUnit)
                .where(CalibrationUnit.window_type == window_type)
                .order_by(
                    CalibrationUnit.category_code,
                    CalibrationUnit.price_bucket,
                    CalibrationUnit.time_bucket,
                    CalibrationUnit.liquidity_tier,
                )
            ).all()
        )

    def _collect_sample_stats(self, window_type: str) -> dict[BucketKey, AggregatedCalibrationStats]:
        grouped_edges: dict[BucketKey, list[float]] = defaultdict(list)

        for market, snapshot in self._load_historical_samples(window_type=window_type):
            implied_probability = midpoint_from_snapshot(snapshot)
            realized_outcome = self._resolved_outcome_for_market(market)

            if implied_probability is None or realized_outcome is None:
                continue

            key = BucketKey(
                category_code=normalize_category(market.category_raw),
                price_bucket=price_bucket_from_probability(implied_probability),
                time_bucket=time_bucket_from_market(market, reference_time=snapshot.snapshot_time),
                liquidity_tier=liquidity_tier_from_snapshot(snapshot),
                window_type=window_type,
            )
            grouped_edges[key].append(float(realized_outcome - implied_probability))

        stats_by_key: dict[BucketKey, AggregatedCalibrationStats] = {}
        for key, edges in grouped_edges.items():
            sample_count = len(edges)
            mean_edge = sum(edges) / sample_count
            std_dev = 0.0
            if sample_count > 1:
                variance = sum((edge - mean_edge) ** 2 for edge in edges) / (sample_count - 1)
                std_dev = math.sqrt(variance)
            margin = 1.96 * std_dev / math.sqrt(sample_count) if sample_count > 1 else 0.0

            is_active = sample_count >= MIN_ACTIVE_SAMPLE_COUNT
            stats_by_key[key] = AggregatedCalibrationStats(
                sample_count=sample_count,
                edge_estimate=quantize_6(Decimal(f"{mean_edge:.6f}")),
                interval_low=quantize_6(Decimal(f"{(mean_edge - margin):.6f}")),
                interval_high=quantize_6(Decimal(f"{(mean_edge + margin):.6f}")),
                is_active=is_active,
                disabled_reason=None if is_active else "insufficient_sample_count",
            )

        return stats_by_key

    def _load_historical_samples(self, window_type: str) -> list[tuple[Market, MarketSnapshot]]:
        lookback_days = WINDOW_LOOKBACK_DAYS.get(window_type, DEFAULT_LOOKBACK_DAYS)
        cutoff = utc_now() - timedelta(days=lookback_days)

        markets = list(
            self.db.scalars(
                select(Market)
                .where(
                    or_(
                        Market.final_resolution.is_not(None),
                        Market.market_status == "resolved",
                    )
                )
                .where(
                    (Market.resolution_time.is_(None)) | (Market.resolution_time >= cutoff)
                )
            ).all()
        )
        if not markets:
            return []

        market_ids = [market.id for market in markets]
        snapshots = list(
            self.db.scalars(
                select(MarketSnapshot)
                .where(MarketSnapshot.market_ref_id.in_(market_ids))
                .order_by(MarketSnapshot.market_ref_id, MarketSnapshot.snapshot_time.desc())
            ).all()
        )
        if not snapshots:
            return []

        market_by_id = {market.id: market for market in markets}
        first_snapshot_by_market: dict[uuid.UUID, MarketSnapshot] = {}
        selected_snapshot_by_market: dict[uuid.UUID, MarketSnapshot] = {}

        for snapshot in snapshots:
            first_snapshot_by_market.setdefault(snapshot.market_ref_id, snapshot)

            market = market_by_id.get(snapshot.market_ref_id)
            if market is None:
                continue

            snapshot_cutoff = market.close_time or market.resolution_time
            if snapshot_cutoff and snapshot.snapshot_time > snapshot_cutoff:
                continue

            selected_snapshot_by_market.setdefault(snapshot.market_ref_id, snapshot)

        results: list[tuple[Market, MarketSnapshot]] = []
        for market in markets:
            snapshot = selected_snapshot_by_market.get(market.id) or first_snapshot_by_market.get(market.id)
            if snapshot is None:
                continue
            results.append((market, snapshot))

        return results

    def _resolved_outcome_for_market(self, market: Market) -> Decimal | None:
        resolution = normalize_binary_resolution(market.final_resolution) or infer_binary_resolution_from_source_payload(
            market.source_payload
        )
        return outcome_from_resolution(resolution)

    def _upsert_unit(
        self,
        *,
        key: BucketKey,
        stats: AggregatedCalibrationStats | None,
        now,
    ) -> CalibrationUnit:
        stmt = select(CalibrationUnit).where(
            CalibrationUnit.category_code == key.category_code,
            CalibrationUnit.price_bucket == key.price_bucket,
            CalibrationUnit.time_bucket == key.time_bucket,
            CalibrationUnit.liquidity_tier == key.liquidity_tier,
            CalibrationUnit.window_type == key.window_type,
        )
        unit = self.db.scalar(stmt)

        if unit is None:
            unit = CalibrationUnit(
                id=uuid.uuid4(),
                category_code=key.category_code,
                price_bucket=key.price_bucket,
                time_bucket=key.time_bucket,
                liquidity_tier=key.liquidity_tier,
                window_type=key.window_type,
                sample_count=0,
                edge_estimate=Decimal("0"),
                interval_low=Decimal("0"),
                interval_high=Decimal("0"),
                is_active=False,
                computed_at=now,
            )
            self.db.add(unit)

        if stats is None:
            unit.sample_count = 0
            unit.edge_estimate = Decimal("0")
            unit.interval_low = Decimal("0")
            unit.interval_high = Decimal("0")
            unit.is_active = False
            unit.disabled_reason = "no_historical_samples"
        else:
            unit.sample_count = stats.sample_count
            unit.edge_estimate = stats.edge_estimate
            unit.interval_low = stats.interval_low
            unit.interval_high = stats.interval_high
            unit.is_active = stats.is_active
            unit.disabled_reason = stats.disabled_reason

        unit.computed_at = now
        self.db.flush()
        return unit

    def _unit_key(self, unit: CalibrationUnit) -> BucketKey:
        return BucketKey(
            category_code=unit.category_code,
            price_bucket=unit.price_bucket,
            time_bucket=unit.time_bucket,
            liquidity_tier=unit.liquidity_tier,
            window_type=unit.window_type,
        )
