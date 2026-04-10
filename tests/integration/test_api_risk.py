"""Integration tests for M4 risk API."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, MarketClassificationResult, NetEVCandidate, RiskThresholdConfig
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_candidate(*, market_code: str, category: str, net_ev: str, decision: str = "admit") -> None:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id=market_code,
                question=f"{market_code} question?",
                category_raw=category,
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=1),
                open_time=now - timedelta(days=1),
                close_time=now + timedelta(days=1),
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
    finally:
        session.close()


def _seed_candidate_for_market(
    *,
    market_id: uuid.UUID,
    net_ev: str,
    decision: str = "admit",
    evaluated_at: datetime | None = None,
) -> None:
    session = TestSessionLocal()
    try:
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
    finally:
        session.close()


def test_get_risk_state_defaults_to_normal(client):
    response = client.get("/risk/state")

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "Normal"
    assert data["history"] == []


def test_compute_exposures_endpoint_auto_transitions_state(client):
    _seed_candidate(market_code="api-risk-1", category="Politics", net_ev="8.80")

    response = client.post("/risk/exposures/compute")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload["exposures"]) == 1
    assert payload["exposures"][0]["cluster_code"] == "Politics"
    assert payload["exposures"][0]["is_breached"] is True

    state_response = client.get("/risk/state")
    assert state_response.status_code == 200
    state_data = state_response.json()
    assert state_data["state"] == "RiskOff"
    assert state_data["history"][0]["to_state"] == "RiskOff"


def test_compute_exposures_endpoint_uses_latest_candidate_only(client):
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id="api-risk-latest-only",
                question="api-risk-latest-only question?",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=1),
                open_time=now - timedelta(days=1),
                close_time=now + timedelta(days=1),
                source_updated_at=now,
            )
        )
        session.add(
            NetEVCandidate(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                calibration_unit_id=None,
                gross_edge=Decimal("6.500000"),
                fee_cost=Decimal("0.010000"),
                slippage_cost=Decimal("0.005000"),
                dispute_discount=Decimal("0.002000"),
                net_ev=Decimal("6.500000"),
                admission_decision="admit",
                rejection_reason_code=None,
                evaluated_at=now,
            )
        )
        session.commit()
    finally:
        session.close()

    _seed_candidate_for_market(
        market_id=market_id,
        net_ev="-0.300000",
        decision="reject",
        evaluated_at=now + timedelta(minutes=1),
    )

    response = client.post("/risk/exposures/compute")
    assert response.status_code == 200
    assert response.json()["exposures"] == []


def test_compute_exposures_endpoint_prefers_structured_cluster(client):
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id="api-risk-structured-cluster",
                question="api-risk-structured-cluster question?",
                category_raw="Up or Down",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=1),
                open_time=now - timedelta(days=1),
                close_time=now + timedelta(days=1),
                source_updated_at=now,
            )
        )
        session.add(
            NetEVCandidate(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                calibration_unit_id=None,
                gross_edge=Decimal("4.200000"),
                fee_cost=Decimal("0.010000"),
                slippage_cost=Decimal("0.005000"),
                dispute_discount=Decimal("0.002000"),
                net_ev=Decimal("4.200000"),
                admission_decision="admit",
                rejection_reason_code=None,
                evaluated_at=now,
            )
        )
        session.add(
            MarketClassificationResult(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                rule_version="tag_default_v1",
                source_fingerprint="api-risk-structured-cluster",
                classification_status="Tagged",
                primary_category_code="CAT_NUMERIC",
                admission_bucket_code="LIST_WHITE",
                confidence=Decimal("0.940000"),
                requires_review=False,
                conflict_count=0,
                failure_reason_code=None,
                result_details={
                    "summary": {
                        "primary_category_code": "CAT_NUMERIC",
                        "risk_factor_codes": ["RF_SINGLE_ASSET_CORRELATED"],
                    }
                },
                classified_at=now,
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.post("/risk/exposures/compute")
    assert response.status_code == 200

    exposures = response.json()["exposures"]
    assert len(exposures) == 1
    assert exposures[0]["cluster_code"] == "CAT_NUMERIC:RF_SINGLE_ASSET_CORRELATED"


def test_get_state_history_returns_event_details(client):
    _seed_candidate(market_code="api-risk-history", category="Politics", net_ev="8.80")

    compute_response = client.post("/risk/exposures/compute")
    assert compute_response.status_code == 200

    history_response = client.get("/risk/state/history")
    assert history_response.status_code == 200

    events = history_response.json()["events"]
    assert len(events) == 1
    assert events[0]["id"]
    assert events[0]["to_state"] == "RiskOff"
    assert events[0]["threshold_value"] == 0.8


def test_kill_switch_request_and_approval_flow(client):
    create_response = client.post(
        "/risk/kill-switch",
        json={
            "request_type": "freeze",
            "target_scope": "global",
            "requested_by": "ops_user",
            "reason": "Freeze the system for review",
        },
    )
    assert create_response.status_code == 200

    created = create_response.json()["request"]
    assert created["status"] == "pending"

    approve_response = client.post(
        f"/risk/kill-switch/{created['id']}/approve",
        json={"reviewer": "risk_lead", "notes": "Approved"},
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()["request"]
    assert approved["status"] == "approved"
    assert approved["reviewed_by"] == "risk_lead"

    state_response = client.get("/risk/state")
    assert state_response.status_code == 200
    assert state_response.json()["state"] == "Frozen"


def test_create_kill_switch_request_rejects_unknown_type(client):
    response = client.post(
        "/risk/kill-switch",
        json={
            "request_type": "pause_everything",
            "target_scope": "global",
            "requested_by": "ops_user",
            "reason": "not valid",
        },
    )

    assert response.status_code == 400
    assert "request_type must be one of" in response.json()["detail"]


def test_list_thresholds_returns_active_rows(client):
    session = TestSessionLocal()
    try:
        session.add(
            RiskThresholdConfig(
                id=uuid.uuid4(),
                cluster_code="global",
                metric_name="utilization_caution",
                threshold_value=Decimal("0.650000"),
                is_active=True,
                created_by="seed",
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/risk/thresholds")
    assert response.status_code == 200

    data = response.json()
    assert len(data["thresholds"]) == 1
    assert data["thresholds"][0]["cluster_code"] == "global"
    assert data["thresholds"][0]["metric_name"] == "utilization_caution"


def test_upsert_threshold_endpoint_affects_exposure_limit(client):
    threshold_response = client.post(
        "/risk/thresholds",
        json={
            "cluster_code": "global",
            "metric_name": "max_exposure",
            "threshold_value": 20,
            "created_by": "risk_ops",
        },
    )
    assert threshold_response.status_code == 200
    threshold = threshold_response.json()["threshold"]
    assert threshold["cluster_code"] == "global"
    assert threshold["metric_name"] == "max_exposure"
    assert threshold["threshold_value"] == 20

    _seed_candidate(market_code="api-risk-2", category="Politics", net_ev="8.80")

    response = client.post("/risk/exposures/compute")
    assert response.status_code == 200

    payload = response.json()
    assert payload["exposures"][0]["limit_value"] == 20.0
    assert payload["exposures"][0]["is_breached"] is False

    state_response = client.get("/risk/state")
    assert state_response.status_code == 200
    assert state_response.json()["state"] == "Normal"


def test_upsert_threshold_endpoint_rejects_invalid_utilization_value(client):
    response = client.post(
        "/risk/thresholds",
        json={
            "cluster_code": "global",
            "metric_name": "utilization_risk_off",
            "threshold_value": 1.2,
            "created_by": "risk_ops",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "utilization thresholds must be between 0 and 1"


def test_deactivate_threshold_endpoint_restores_default_limit(client):
    threshold_response = client.post(
        "/risk/thresholds",
        json={
            "cluster_code": "global",
            "metric_name": "max_exposure",
            "threshold_value": 20,
            "created_by": "risk_ops",
        },
    )
    assert threshold_response.status_code == 200
    threshold_id = threshold_response.json()["threshold"]["id"]

    deactivate_response = client.post(f"/risk/thresholds/{threshold_id}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["threshold"]["is_active"] is False

    list_response = client.get("/risk/thresholds")
    assert list_response.status_code == 200
    assert list_response.json()["thresholds"] == []

    _seed_candidate(market_code="api-risk-3", category="Politics", net_ev="8.80")

    exposure_response = client.post("/risk/exposures/compute")
    assert exposure_response.status_code == 200
    exposure = exposure_response.json()["exposures"][0]
    assert exposure["limit_value"] == 10.0
    assert exposure["is_breached"] is True


def test_deactivate_threshold_endpoint_returns_404_for_unknown_id(client):
    response = client.post(f"/risk/thresholds/{uuid.uuid4()}/deactivate")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
