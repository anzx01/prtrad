"""Integration tests for M4 risk API."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, NetEVCandidate, RiskThresholdConfig
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
