"""Integration tests for M3 calibration API."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, MarketSnapshot
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_resolved_market(index: int, *, midpoint: str):
    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    midpoint_decimal = Decimal(midpoint)
    market = Market(
        id=market_id,
        market_id=f"api-resolved-{index}",
        question=f"Resolved API market {index}?",
        category_raw="Politics",
        market_status="resolved",
        creation_time=now - timedelta(days=4),
        open_time=now - timedelta(days=3),
        close_time=now - timedelta(days=1),
        resolution_time=now - timedelta(hours=12),
        final_resolution="yes",
        source_updated_at=now - timedelta(hours=6),
    )
    snapshot = MarketSnapshot(
        id=uuid.uuid4(),
        market_ref_id=market_id,
        snapshot_time=now - timedelta(days=1, hours=1),
        best_bid_yes=midpoint_decimal - Decimal("0.01"),
        best_ask_yes=midpoint_decimal + Decimal("0.01"),
        spread=Decimal("0.02"),
        cumulative_depth_at_target_size=Decimal("2500"),
        traded_volume=Decimal("7000"),
        last_trade_age_seconds=20,
    )
    return market, snapshot


def test_compute_calibration_endpoint(client):
    session = TestSessionLocal()
    try:
        for index, midpoint in enumerate(["0.74", "0.76", "0.78", "0.72", "0.70"], start=1):
            market, snapshot = _seed_resolved_market(index, midpoint=midpoint)
            session.add(market)
            session.add(snapshot)
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/calibration/compute",
        json={
            "category_code": "Politics",
            "price_bucket": "p70_90",
            "time_bucket": "d1_3",
            "liquidity_tier": "standard",
            "window_type": "long",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["sample_count"] == 5
    assert data["is_active"] is True
    assert round(data["edge_estimate"], 4) == 0.26


def test_recompute_all_calibration_endpoint(client):
    session = TestSessionLocal()
    try:
        for index, midpoint in enumerate(["0.74", "0.76", "0.78", "0.72", "0.70"], start=1):
            market, snapshot = _seed_resolved_market(index, midpoint=midpoint)
            session.add(market)
            session.add(snapshot)
        session.commit()
    finally:
        session.close()

    response = client.post("/calibration/recompute-all?window_type=long")
    assert response.status_code == 200

    data = response.json()
    assert data["window_type"] == "long"
    assert data["total_units"] >= 1
    assert data["active_units"] >= 1

    list_response = client.get("/calibration/units?include_inactive=true")
    assert list_response.status_code == 200
    units = list_response.json()
    assert len(units) >= 1
