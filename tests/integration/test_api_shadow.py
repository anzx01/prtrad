from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, NetEVCandidate
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_candidate(*, market_code: str, net_ev: str) -> None:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id=market_code,
                question=f"{market_code} question?",
                category_raw="Politics",
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
                admission_decision="admit",
                rejection_reason_code=None,
                evaluated_at=now,
            )
        )
        session.commit()
    finally:
        session.close()


def test_execute_shadow_run_and_list(client):
    _seed_candidate(market_code="api-shadow-1", net_ev="0.090000")

    create_response = client.post(
        "/shadow/execute",
        json={"run_name": "api-shadow", "executed_by": "ops_api"},
    )
    assert create_response.status_code == 200
    run = create_response.json()["run"]
    assert run["run_name"] == "api-shadow"
    assert run["recommendation"] in {"go", "watch", "block"}

    list_response = client.get("/shadow")
    assert list_response.status_code == 200
    assert len(list_response.json()["runs"]) == 1
