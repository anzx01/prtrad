"""Integration tests for M3 NetEV API."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import CalibrationUnit, DataQualityResult, Market, MarketScoringResult, MarketSnapshot
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_candidate_market() -> uuid.UUID:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id="api-candidate-1",
                question="Will the API candidate resolve YES?",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=1),
                open_time=now - timedelta(days=1),
                close_time=now + timedelta(days=1),
                source_updated_at=now,
            )
        )
        session.add(
            CalibrationUnit(
                id=uuid.uuid4(),
                category_code="Politics",
                price_bucket="p70_90",
                time_bucket="d1_3",
                liquidity_tier="standard",
                window_type="long",
                sample_count=12,
                edge_estimate=Decimal("0.060000"),
                interval_low=Decimal("0.030000"),
                interval_high=Decimal("0.090000"),
                is_active=True,
                computed_at=now,
            )
        )
        session.add(
            MarketSnapshot(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                snapshot_time=now,
                best_bid_yes=Decimal("0.75"),
                best_ask_yes=Decimal("0.77"),
                spread=Decimal("0.02"),
                cumulative_depth_at_target_size=Decimal("2500"),
                traded_volume=Decimal("8000"),
                last_trade_age_seconds=30,
            )
        )
        session.add(
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                checked_at=now,
                status="pass",
                score=Decimal("0.99"),
                failure_count=0,
                result_details={"blocking_reason_codes": []},
                rule_version="dq_v1",
            )
        )
        session.add(
            MarketScoringResult(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                classification_result_id=None,
                clarity_score=Decimal("0.88"),
                resolution_objectivity_score=Decimal("0.91"),
                overall_score=Decimal("0.89"),
                admission_recommendation="Approved",
                rejection_reason_code=None,
                scoring_details={"source": "integration-test"},
                scored_at=now,
            )
        )
        session.commit()
        return market_id
    finally:
        session.close()


def test_evaluate_market_endpoint(client):
    market_id = _seed_candidate_market()

    response = client.post(f"/netev/evaluate/{market_id}?window_type=long")
    assert response.status_code == 200

    data = response.json()
    assert data["admission_decision"] == "admit"
    assert data["market_id"] == "api-candidate-1"
    assert data["rule_version"] == "dev"
    assert data["rejection_reason_code"] is None
    assert data["calibration_sample_count"] == 12


def test_evaluate_batch_endpoint(client):
    _seed_candidate_market()

    response = client.post("/netev/evaluate-batch?limit=10&window_type=long")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    assert data["admitted"] >= 1
    assert len(data["candidates"]) >= 1
