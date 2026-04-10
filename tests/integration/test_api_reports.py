from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import AuditLog, Market, NetEVCandidate
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_report_inputs() -> None:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id="api-report-market",
                question="api-report-market question?",
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
                gross_edge=Decimal("0.100000"),
                fee_cost=Decimal("0.010000"),
                slippage_cost=Decimal("0.005000"),
                dispute_discount=Decimal("0.002000"),
                net_ev=Decimal("0.100000"),
                admission_decision="admit",
                rejection_reason_code=None,
                evaluated_at=now - timedelta(hours=1),
            )
        )
        session.add(
            AuditLog(
                id=uuid.uuid4(),
                actor_id="system",
                actor_type="service",
                object_type="netev_candidate",
                object_id="api-report-seed",
                action="evaluate",
                result="success",
                event_payload={"seed": True},
            )
        )
        session.commit()
    finally:
        session.close()


def test_generate_report_and_list_audit(client):
    _seed_report_inputs()

    generate_response = client.post(
        "/reports/generate",
        json={"report_type": "daily_summary", "generated_by": "api_user"},
    )
    assert generate_response.status_code == 200
    report = generate_response.json()["report"]
    assert report["report_type"] == "daily_summary"
    assert report["report_data"]["summary"]["candidate_total"] == 1

    list_response = client.get("/reports")
    assert list_response.status_code == 200
    assert len(list_response.json()["reports"]) == 1

    audit_response = client.get("/reports/audit")
    assert audit_response.status_code == 200
    assert len(audit_response.json()["audit_events"]) >= 1
