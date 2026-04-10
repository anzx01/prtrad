"""Unit tests for M4 risk services."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from sqlalchemy import select

from db.models import Market, MarketClassificationResult, NetEVCandidate, RiskStateEvent
from services.risk.kill_switch import KillSwitchService
from services.risk.service import RiskService


UTC = timezone.utc


def _add_candidate(
    session,
    *,
    market_code: str,
    category: str,
    net_ev: str,
    decision: str = "admit",
) -> uuid.UUID:
    now = datetime.now(UTC)
    market_id = uuid.uuid4()

    session.add(
        Market(
            id=market_id,
            market_id=market_code,
            question=f"{market_code} question?",
            category_raw=category,
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=2),
            close_time=now + timedelta(days=2),
            source_updated_at=now,
        )
    )
    session.add(
        NetEVCandidate(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            calibration_unit_id=None,
            gross_edge=Decimal(net_ev),
            fee_cost=Decimal("0.010000"),
            slippage_cost=Decimal("0.005000"),
            dispute_discount=Decimal("0.002000"),
            net_ev=Decimal(net_ev),
            admission_decision=decision,
            rejection_reason_code=None if decision == "admit" else "REJ_COST_NEG_NETEV",
            evaluated_at=now,
        )
    )
    session.commit()
    return market_id


def _add_candidate_for_existing_market(
    session,
    *,
    market_id: uuid.UUID,
    net_ev: str,
    decision: str = "admit",
    evaluated_at: datetime | None = None,
) -> None:
    now = evaluated_at or datetime.now(UTC)
    session.add(
        NetEVCandidate(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            calibration_unit_id=None,
            gross_edge=Decimal(net_ev),
            fee_cost=Decimal("0.010000"),
            slippage_cost=Decimal("0.005000"),
            dispute_discount=Decimal("0.002000"),
            net_ev=Decimal(net_ev),
            admission_decision=decision,
            rejection_reason_code=None if decision == "admit" else "REJ_COST_NEG_NETEV",
            evaluated_at=now,
        )
    )
    session.commit()


def test_compute_exposure_aggregates_admitted_candidates(test_db):
    session = test_db()
    service = RiskService(session)

    _add_candidate(session, market_code="risk-1", category="Politics", net_ev="3.25")
    _add_candidate(session, market_code="risk-2", category="Politics", net_ev="1.75")
    _add_candidate(
        session,
        market_code="risk-3",
        category="Sports",
        net_ev="-1.00",
        decision="reject",
    )

    exposures = service.compute_exposure()

    assert len(exposures) == 1
    assert exposures[0].cluster_code == "Politics"
    assert float(exposures[0].gross_exposure) == 5.0
    assert float(exposures[0].net_exposure) == 5.0
    assert exposures[0].position_count == 2
    assert float(exposures[0].limit_value) == 10.0
    assert exposures[0].is_breached is False

    latest = service.list_exposures()
    assert len(latest) == 1
    assert latest[0].cluster_code == "Politics"

    session.close()


def test_compute_exposure_uses_latest_candidate_per_market(test_db):
    session = test_db()
    service = RiskService(session)

    market_id = _add_candidate(
        session,
        market_code="risk-latest-only",
        category="Politics",
        net_ev="3.25",
    )
    _add_candidate_for_existing_market(
        session,
        market_id=market_id,
        net_ev="-0.50",
        decision="reject",
        evaluated_at=datetime.now(UTC) + timedelta(minutes=1),
    )

    exposures = service.compute_exposure()

    assert exposures == []
    session.close()


def test_compute_exposure_prefers_structured_cluster_code(test_db):
    session = test_db()
    service = RiskService(session)

    market_id = _add_candidate(
        session,
        market_code="risk-structured-cluster",
        category="Up or Down",
        net_ev="4.50",
    )
    session.add(
        MarketClassificationResult(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            rule_version="tag_default_v1",
            source_fingerprint="structured-risk-cluster",
            classification_status="Tagged",
            primary_category_code="CAT_NUMERIC",
            admission_bucket_code="LIST_WHITE",
            confidence=Decimal("0.92"),
            requires_review=False,
            conflict_count=0,
            failure_reason_code=None,
            result_details={
                "summary": {
                    "primary_category_code": "CAT_NUMERIC",
                    "risk_factor_codes": ["RF_SINGLE_ASSET_CORRELATED"],
                }
            },
            classified_at=datetime.now(UTC),
        )
    )
    session.commit()

    exposures = service.compute_exposure()

    assert len(exposures) == 1
    assert exposures[0].cluster_code == "CAT_NUMERIC:RF_SINGLE_ASSET_CORRELATED"
    session.close()


def test_check_and_auto_transition_promotes_to_risk_off(test_db):
    session = test_db()
    service = RiskService(session)

    _add_candidate(session, market_code="risk-4", category="Crypto", net_ev="8.50")
    service.compute_exposure()

    event = service.check_and_auto_transition()

    assert event is not None
    assert event.from_state == "Normal"
    assert event.to_state == "RiskOff"
    assert service.get_current_state() == "RiskOff"
    assert service.check_and_auto_transition() is None

    session.close()


def test_kill_switch_approve_creates_manual_state_event(test_db):
    session = test_db()
    service = KillSwitchService(session)

    request = service.request_action(
        request_type="freeze",
        target_scope="global",
        requested_by="ops_a",
        reason="Manual freeze for investigation",
    )
    approved = service.approve(request.id, reviewer="lead_reviewer", notes="Approved")

    assert approved.status == "approved"
    assert approved.reviewed_by == "lead_reviewer"

    events = list(
        session.scalars(
            select(RiskStateEvent).order_by(RiskStateEvent.created_at.desc())
        ).all()
    )
    assert len(events) == 1
    assert events[0].trigger_type == "manual"
    assert events[0].to_state == "Frozen"

    risk_service = RiskService(session)
    assert risk_service.get_current_state() == "Frozen"

    session.close()


def test_upsert_threshold_updates_existing_row(test_db):
    session = test_db()
    service = RiskService(session)

    created = service.upsert_threshold(
        cluster_code="global",
        metric_name="max_exposure",
        threshold_value=Decimal("12.500000"),
        created_by="risk_ops",
    )
    updated = service.upsert_threshold(
        cluster_code="global",
        metric_name="max_exposure",
        threshold_value=Decimal("18.000000"),
        created_by="risk_admin",
    )

    assert updated.id == created.id
    assert float(updated.threshold_value) == 18.0
    assert updated.created_by == "risk_admin"
    assert len(service.list_thresholds()) == 1

    session.close()


def test_deactivate_threshold_removes_active_override(test_db):
    session = test_db()
    service = RiskService(session)

    created = service.upsert_threshold(
        cluster_code="global",
        metric_name="max_exposure",
        threshold_value=Decimal("20.000000"),
        created_by="risk_ops",
    )

    deactivated = service.deactivate_threshold(created.id)

    assert deactivated.id == created.id
    assert deactivated.is_active is False
    assert service.list_thresholds() == []

    session.close()


def test_cluster_threshold_override_takes_precedence_over_global(test_db):
    session = test_db()
    service = RiskService(session)

    service.upsert_threshold(
        cluster_code="global",
        metric_name="max_exposure",
        threshold_value=Decimal("20.000000"),
        created_by="risk_ops",
    )
    service.upsert_threshold(
        cluster_code="CAT_NUMERIC",
        metric_name="max_exposure",
        threshold_value=Decimal("5.000000"),
        created_by="risk_ops",
    )

    market_id = _add_candidate(
        session,
        market_code="risk-cluster-threshold",
        category="Up or Down",
        net_ev="4.50",
    )
    session.add(
        MarketClassificationResult(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            rule_version="tag_default_v1",
            source_fingerprint="cluster-threshold-priority",
            classification_status="Tagged",
            primary_category_code="CAT_NUMERIC",
            admission_bucket_code="LIST_WHITE",
            confidence=Decimal("0.92"),
            requires_review=False,
            conflict_count=0,
            failure_reason_code=None,
            result_details={"summary": {"primary_category_code": "CAT_NUMERIC"}},
            classified_at=datetime.now(UTC),
        )
    )
    session.commit()

    exposures = service.compute_exposure()

    assert len(exposures) == 1
    assert exposures[0].cluster_code == "CAT_NUMERIC"
    assert float(exposures[0].limit_value) == 5.0
    assert exposures[0].is_breached is True

    session.close()
