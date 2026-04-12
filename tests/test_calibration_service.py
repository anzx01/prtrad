"""Unit tests for M3 calibration service."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, MarketSnapshot
from services.calibration.service import CalibrationService


UTC = timezone.utc


def _resolved_market(
    index: int,
    *,
    outcome: str | None,
    midpoint: str,
    category: str = "Politics",
    source_outcome_prices: list[str] | None = None,
) -> tuple[Market, MarketSnapshot]:
    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    midpoint_decimal = Decimal(midpoint)
    bid_yes = midpoint_decimal - Decimal("0.01")
    ask_yes = midpoint_decimal + Decimal("0.01")

    market = Market(
        id=market_id,
        market_id=f"resolved-{index}",
        question=f"Resolved market {index}?",
        category_raw=category,
        market_status="resolved",
        creation_time=now - timedelta(days=4),
        open_time=now - timedelta(days=3),
        close_time=now - timedelta(days=1),
        resolution_time=now - timedelta(hours=12),
        final_resolution=outcome,
        source_payload={"market": {"outcome_prices": source_outcome_prices or []}},
        source_updated_at=now - timedelta(hours=10),
    )
    snapshot = MarketSnapshot(
        id=uuid.uuid4(),
        market_ref_id=market_id,
        snapshot_time=now - timedelta(days=1, hours=1),
        best_bid_yes=bid_yes,
        best_ask_yes=ask_yes,
        spread=ask_yes - bid_yes,
        cumulative_depth_at_target_size=Decimal("2500"),
        traded_volume=Decimal("6000"),
        last_trade_age_seconds=30,
    )
    return market, snapshot


def test_compute_calibration_aggregates_resolved_markets(test_db):
    session = test_db()
    service = CalibrationService(session)

    samples = [
        _resolved_market(1, outcome="yes", midpoint="0.74"),
        _resolved_market(2, outcome="yes", midpoint="0.76"),
        _resolved_market(3, outcome="yes", midpoint="0.78"),
        _resolved_market(4, outcome="yes", midpoint="0.72"),
        _resolved_market(5, outcome="yes", midpoint="0.70"),
    ]
    for market, snapshot in samples:
        session.add(market)
        session.add(snapshot)
    session.commit()

    unit = service.compute_calibration(
        category_code="Politics",
        price_bucket="p70_90",
        time_bucket="d1_3",
        liquidity_tier="standard",
        window_type="long",
    )

    assert unit.sample_count == 5
    assert unit.is_active is True
    assert round(float(unit.edge_estimate), 4) == 0.2600
    assert unit.disabled_reason is None

    session.close()


def test_compute_calibration_infers_resolution_from_source_payload(test_db):
    session = test_db()
    service = CalibrationService(session)

    samples = [
        _resolved_market(11, outcome=None, midpoint="0.74", source_outcome_prices=["1", "0"]),
        _resolved_market(12, outcome=None, midpoint="0.76", source_outcome_prices=["1", "0"]),
        _resolved_market(13, outcome=None, midpoint="0.78", source_outcome_prices=["1", "0"]),
        _resolved_market(14, outcome=None, midpoint="0.72", source_outcome_prices=["1", "0"]),
        _resolved_market(15, outcome=None, midpoint="0.70", source_outcome_prices=["1", "0"]),
    ]
    for market, snapshot in samples:
        session.add(market)
        session.add(snapshot)
    session.commit()

    unit = service.compute_calibration(
        category_code="Politics",
        price_bucket="p70_90",
        time_bucket="d1_3",
        liquidity_tier="standard",
        window_type="long",
    )

    assert unit.sample_count == 5
    assert unit.is_active is True
    assert round(float(unit.edge_estimate), 4) == 0.2600
    session.close()


def test_compute_calibration_marks_unit_inactive_when_samples_are_missing(test_db):
    session = test_db()
    service = CalibrationService(session)

    unit = service.compute_calibration(
        category_code="Sports",
        price_bucket="p30_50",
        time_bucket="d1_3",
        liquidity_tier="standard",
        window_type="long",
    )

    assert unit.sample_count == 0
    assert unit.is_active is False
    assert unit.disabled_reason == "no_historical_samples"

    session.close()

