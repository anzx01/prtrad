from datetime import UTC, datetime, timedelta
from decimal import Decimal
import uuid

from db.models import Market, MarketSnapshot, NetEVCandidate
from services.paper_trading import PaperTradingService


def _seed_admitted_market(session, *, market_code: str = "paper-svc-1") -> uuid.UUID:
    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    session.add(
        Market(
            id=market_id,
            market_id=market_code,
            question="Will the paper trading service work?",
            category_raw="Politics",
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=2),
            close_time=now + timedelta(days=2),
            clob_token_ids=["yes-token", "no-token"],
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


def test_evaluate_candidates_opens_no_position(test_db):
    session = test_db()
    try:
        _seed_admitted_market(session)
        service = PaperTradingService(session)

        result = service.evaluate_candidates(limit=10)
        session.commit()

        assert result["created_count"] == 1
        position = service.list_positions(status="open")[0]
        assert position.side == "no"
        assert position.entry_price == Decimal("0.450000")
        assert position.mark_price == Decimal("0.420000")
        assert position.unrealized_pnl == Decimal("-0.300000")
    finally:
        session.close()


def test_evaluate_candidates_does_not_duplicate_open_position(test_db):
    session = test_db()
    try:
        _seed_admitted_market(session)
        service = PaperTradingService(session)

        first = service.evaluate_candidates(limit=10)
        second = service.evaluate_candidates(limit=10)
        session.commit()

        assert first["created_count"] == 1
        assert second["created_count"] == 0
        assert second["skipped"][0]["reason"] == "OPEN_POSITION_EXISTS"
        assert len(service.list_positions(status="open")) == 1
    finally:
        session.close()


def test_mark_positions_updates_unrealized_pnl(test_db):
    session = test_db()
    try:
        market_id = _seed_admitted_market(session)
        service = PaperTradingService(session)
        service.evaluate_candidates(limit=10)

        now = datetime.now(UTC) + timedelta(minutes=5)
        session.add(
            MarketSnapshot(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                snapshot_time=now,
                best_bid_no=Decimal("0.500000"),
                best_ask_no=Decimal("0.530000"),
                best_bid_yes=Decimal("0.470000"),
                best_ask_yes=Decimal("0.500000"),
                last_trade_price_no=Decimal("0.510000"),
                spread=Decimal("0.030000"),
                top_of_book_depth=Decimal("5000"),
                cumulative_depth_at_target_size=Decimal("8000"),
                trade_count=21,
                traded_volume=Decimal("12100"),
                last_trade_age_seconds=10,
            )
        )
        session.commit()

        result = service.mark_positions(auto_close=False)
        position = service.list_positions(status="open")[0]

        assert result["updated_count"] == 1
        assert position.mark_price == Decimal("0.500000")
        assert position.unrealized_pnl == Decimal("0.500000")
    finally:
        session.close()


def test_mark_positions_closes_resolved_market(test_db):
    session = test_db()
    try:
        market_id = _seed_admitted_market(session)
        service = PaperTradingService(session)
        service.evaluate_candidates(limit=10)

        market = session.get(Market, market_id)
        market.final_resolution = "no"
        market.market_status = "resolved"
        session.commit()

        result = service.mark_positions()
        closed = service.list_positions(status="closed")[0]

        assert result["closed_count"] == 1
        assert closed.exit_reason == "resolved"
        assert closed.exit_price == Decimal("1.000000")
        assert closed.realized_pnl == Decimal("5.500000")
        assert service.get_summary()["win_rate"] == 1.0
    finally:
        session.close()
