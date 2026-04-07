"""Unit tests for M3 NetEV service."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import (
    CalibrationUnit,
    DataQualityResult,
    DecisionLog,
    Market,
    MarketScoringResult,
    RejectionReasonStats,
    NetEVCandidate,
)
from services.netev.service import NetEVService


UTC = timezone.utc


def _candidate_market() -> tuple[Market, uuid.UUID]:
    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    market = Market(
        id=market_id,
        market_id="candidate-1",
        question="Will the test candidate resolve YES?",
        category_raw="Politics",
        market_status="active_accepting_orders",
        creation_time=now - timedelta(days=1),
        open_time=now - timedelta(days=1),
        close_time=now + timedelta(days=1),
        source_updated_at=now,
    )
    return market, market_id


def test_evaluate_market_admits_when_cost_adjusted_edge_is_positive(test_db):
    session = test_db()
    service = NetEVService(session)
    now = datetime.now(UTC)

    market, market_id = _candidate_market()
    session.add(market)
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
        DataQualityResult(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            checked_at=now,
            status="pass",
            score=Decimal("0.98"),
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
            scoring_details={"source": "unit-test"},
            scored_at=now,
        )
    )
    from db.models import MarketSnapshot

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
            last_trade_age_seconds=25,
        )
    )
    session.commit()

    candidate = service.evaluate(market_id, window_type="long")

    assert candidate is not None
    assert candidate.admission_decision == "admit"
    assert candidate.rejection_reason_code is None
    assert float(candidate.net_ev) > 0.02

    persisted_log = session.query(DecisionLog).filter(DecisionLog.signal_id == str(candidate.id)).one()
    assert persisted_log.decision_type == "netev_admission"
    assert persisted_log.rule_version == "dev"

    session.close()


def test_evaluate_market_rejects_when_calibration_unit_is_missing(test_db):
    session = test_db()
    service = NetEVService(session)
    now = datetime.now(UTC)

    market, market_id = _candidate_market()
    session.add(market)
    session.add(
        DataQualityResult(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            checked_at=now,
            status="pass",
            score=Decimal("0.98"),
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
            clarity_score=Decimal("0.86"),
            resolution_objectivity_score=Decimal("0.90"),
            overall_score=Decimal("0.88"),
            admission_recommendation="Approved",
            rejection_reason_code=None,
            scoring_details={"source": "unit-test"},
            scored_at=now,
        )
    )
    from db.models import MarketSnapshot

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
            last_trade_age_seconds=25,
        )
    )
    session.commit()

    candidate = service.evaluate(market_id, window_type="long")

    assert candidate is not None
    assert candidate.admission_decision == "reject"
    assert candidate.rejection_reason_code == "CALIBRATION_UNIT_MISSING"

    reason_stats = session.query(RejectionReasonStats).filter(
        RejectionReasonStats.reason_code == "CALIBRATION_UNIT_MISSING"
    ).one()
    assert reason_stats.occurrence_count == 1

    session.close()
