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
        previous_day_midday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=12)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id="api-report-market",
                question="api-report-market question?",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=previous_day_midday - timedelta(days=1),
                open_time=previous_day_midday - timedelta(days=1),
                close_time=previous_day_midday + timedelta(days=1),
                source_updated_at=previous_day_midday,
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
                evaluated_at=previous_day_midday,
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
                created_at=previous_day_midday + timedelta(hours=1),
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


def test_generate_daily_report_reuses_same_window_record(client):
    _seed_report_inputs()

    first_response = client.post(
        "/reports/generate",
        json={"report_type": "daily_summary", "generated_by": "api_user_a"},
    )
    assert first_response.status_code == 200
    first_report = first_response.json()["report"]

    second_response = client.post(
        "/reports/generate",
        json={"report_type": "daily_summary", "generated_by": "api_user_b"},
    )
    assert second_response.status_code == 200
    second_report = second_response.json()["report"]

    list_response = client.get("/reports?report_type=daily_summary")
    assert list_response.status_code == 200
    reports = list_response.json()["reports"]
    assert len(reports) == 1
    assert first_report["id"] == second_report["id"]
    assert reports[0]["generated_by"] == "api_user_b"
