from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, NetEVCandidate
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_candidate(*, market_code: str, net_ev: str, decision: str = "admit") -> None:
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
                admission_decision=decision,
                rejection_reason_code=None if decision == "admit" else "REJ_COST_NEG_NETEV",
                evaluated_at=now - timedelta(minutes=10),
            )
        )
        session.commit()
    finally:
        session.close()


def test_create_and_list_backtest_runs(client):
    _seed_candidate(market_code="api-bt-1", net_ev="0.120000")

    create_response = client.post(
        "/backtests/run",
        json={
            "run_name": "api-backtest",
            "window_days": 30,
            "executed_by": "research_api",
            "strategy_version": "baseline-v1",
        },
    )
    assert create_response.status_code == 200
    run = create_response.json()["run"]
    assert run["run_name"] == "api-backtest"
    assert run["summary"]["totals"]["candidate_count"] == 1

    list_response = client.get("/backtests")
    assert list_response.status_code == 200
    runs = list_response.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["id"] == run["id"]
