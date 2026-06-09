from datetime import UTC, datetime, timedelta
from decimal import Decimal
import uuid

from db.models import Market, MarketSnapshot, NetEVCandidate
from tests.integration.conftest import TestSessionLocal


def _seed_api_paper_market() -> uuid.UUID:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id="api-paper-1",
                question="Will the paper trading API work?",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=2),
                open_time=now - timedelta(days=2),
                close_time=now + timedelta(days=2),
                clob_token_ids=["yes-token-api", "no-token-api"],
                outcomes=["Yes", "No"],
                source_updated_at=now,
            )
        )
        session.add(
            MarketSnapshot(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                snapshot_time=now,
                best_bid_no=Decimal("0.420000"),
                best_ask_no=Decimal("0.450000"),
                best_bid_yes=Decimal("0.550000"),
                best_ask_yes=Decimal("0.580000"),
                last_trade_price_no=Decimal("0.440000"),
                spread=Decimal("0.030000"),
                top_of_book_depth=Decimal("5000"),
                cumulative_depth_at_target_size=Decimal("8000"),
                trade_count=20,
                traded_volume=Decimal("12000"),
                last_trade_age_seconds=30,
            )
        )
        session.add(
            NetEVCandidate(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                calibration_unit_id=None,
                gross_edge=Decimal("0.090000"),
                fee_cost=Decimal("0.010000"),
                slippage_cost=Decimal("0.005000"),
                dispute_discount=Decimal("0.002000"),
                net_ev=Decimal("0.073000"),
                admission_decision="admit",
                rejection_reason_code=None,
                evaluated_at=now,
            )
        )
        session.commit()
        return market_id
    finally:
        session.close()


def _add_snapshot(market_id: uuid.UUID, *, bid_no: str) -> None:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC) + timedelta(minutes=5)
        session.add(
            MarketSnapshot(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                snapshot_time=now,
                best_bid_no=Decimal(bid_no),
                best_ask_no=Decimal("0.530000"),
                best_bid_yes=Decimal("0.470000"),
                best_ask_yes=Decimal("0.500000"),
                last_trade_price_no=Decimal(bid_no),
                spread=Decimal("0.030000"),
                top_of_book_depth=Decimal("5000"),
                cumulative_depth_at_target_size=Decimal("8000"),
                trade_count=21,
                traded_volume=Decimal("12100"),
                last_trade_age_seconds=10,
            )
        )
        session.commit()
    finally:
        session.close()


def _resolve_market(market_id: uuid.UUID, *, final_resolution: str) -> None:
    session = TestSessionLocal()
    try:
        market = session.get(Market, market_id)
        market.final_resolution = final_resolution
        market.market_status = "resolved"
        session.commit()
    finally:
        session.close()


def test_paper_trading_api_runs_position_lifecycle(client):
    market_id = _seed_api_paper_market()

    summary_response = client.get("/paper-trading/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["summary"]["total_count"] == 0

    evaluate_response = client.post(
        "/paper-trading/evaluate",
        json={"limit": 10, "strategy_version": "api-paper-v1"},
    )
    assert evaluate_response.status_code == 200
    evaluate_payload = evaluate_response.json()
    assert evaluate_payload["result"]["created_count"] == 1
    assert evaluate_payload["summary"]["open_count"] == 1

    positions_response = client.get("/paper-trading/positions?status=open")
    assert positions_response.status_code == 200
    positions = positions_response.json()["positions"]
    assert len(positions) == 1
    assert positions[0]["market_id"] == "api-paper-1"
    assert positions[0]["side"] == "no"
    assert positions[0]["entry_price"] == 0.45

    _add_snapshot(market_id, bid_no="0.500000")
    mark_response = client.post("/paper-trading/mark", json={"auto_close": False})
    assert mark_response.status_code == 200
    mark_payload = mark_response.json()
    assert mark_payload["result"]["updated_count"] == 1
    assert mark_payload["summary"]["unrealized_pnl"] == 0.5

    _resolve_market(market_id, final_resolution="no")
    close_response = client.post("/paper-trading/mark", json={"auto_close": True})
    assert close_response.status_code == 200
    close_payload = close_response.json()
    assert close_payload["result"]["closed_count"] == 1
    assert close_payload["summary"]["open_count"] == 0
    assert close_payload["summary"]["closed_count"] == 1
    assert close_payload["summary"]["realized_pnl"] == 5.5
    assert close_payload["summary"]["win_rate"] == 1.0

    closed_response = client.get("/paper-trading/positions?status=closed")
    assert closed_response.status_code == 200
    closed = closed_response.json()["positions"]
    assert closed[0]["exit_reason"] == "resolved"
    assert closed[0]["exit_price"] == 1.0
