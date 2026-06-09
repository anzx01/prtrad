"""
Unit tests for data quality service.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from db.models import DataQualityResult, Market, MarketSnapshot
from services.dq.service import MarketDataQualityService


@pytest.fixture
def sample_market(test_db):
    """Create a sample market for testing."""
    session = test_db()
    market = Market(
        market_id="test_market_1",
        question="Will this test pass?",
        description="A test market",
        market_status="active_accepting_orders",
        outcomes=["Yes", "No"],
        clob_token_ids=["token1", "token2"],
    )
    session.add(market)
    session.commit()
    market_id = market.id
    session.close()
    return market_id


def test_dq_service_initialization(test_settings):
    """Test that DQ service initializes correctly."""
    service = MarketDataQualityService(test_settings)
    assert service._settings == test_settings


def test_evaluate_markets_empty(test_db, test_settings, monkeypatch):
    """Test DQ evaluation with no markets."""
    # Mock session_scope to use test database
    import services.dq.service as dq_service_module

    def mock_session_scope():
        from contextlib import contextmanager

        @contextmanager
        def _scope():
            s = test_db()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        return _scope()

    monkeypatch.setattr(dq_service_module, "session_scope", mock_session_scope)

    service = MarketDataQualityService(test_settings)
    checked_at = datetime.now(UTC)
    result = service.evaluate_markets(checked_at=checked_at, market_limit=10)

    assert result["selected_markets"] == 0
    assert result["created"] == 0


def test_evaluate_markets_with_snapshot(test_db, test_settings, sample_market, monkeypatch):
    """Test DQ evaluation with a market and snapshot."""
    import services.dq.service as dq_service_module

    def mock_session_scope():
        from contextlib import contextmanager

        @contextmanager
        def _scope():
            s = test_db()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        return _scope()

    monkeypatch.setattr(dq_service_module, "session_scope", mock_session_scope)

    # Add a snapshot
    session = test_db()
    snapshot = MarketSnapshot(
        market_ref_id=sample_market,
        snapshot_time=datetime.now(UTC),
        best_bid_no=Decimal("0.45"),
        best_ask_no=Decimal("0.55"),
        best_bid_yes=Decimal("0.45"),
        best_ask_yes=Decimal("0.55"),
        spread=Decimal("0.10"),
        top_of_book_depth=Decimal("1000"),
        cumulative_depth_at_target_size=Decimal("500"),
        traded_volume=Decimal("10000"),
    )
    session.add(snapshot)
    session.commit()
    session.close()

    service = MarketDataQualityService(test_settings)
    checked_at = datetime.now(UTC)
    result = service.evaluate_markets(checked_at=checked_at, market_limit=10)

    assert result["selected_markets"] == 1
    assert result["created"] == 1
    assert result["pass"] + result["warn"] + result["fail"] == 1


def test_dq_idempotency(test_db, test_settings, sample_market, monkeypatch):
    """Test that DQ evaluation is idempotent."""
    import services.dq.service as dq_service_module

    def mock_session_scope():
        from contextlib import contextmanager

        @contextmanager
        def _scope():
            s = test_db()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        return _scope()

    monkeypatch.setattr(dq_service_module, "session_scope", mock_session_scope)

    # Add a snapshot
    session = test_db()
    snapshot = MarketSnapshot(
        market_ref_id=sample_market,
        snapshot_time=datetime.now(UTC),
        best_bid_no=Decimal("0.45"),
        best_ask_no=Decimal("0.55"),
        best_bid_yes=Decimal("0.45"),
        best_ask_yes=Decimal("0.55"),
        spread=Decimal("0.10"),
        top_of_book_depth=Decimal("1000"),
        cumulative_depth_at_target_size=Decimal("500"),
        traded_volume=Decimal("10000"),
    )
    session.add(snapshot)
    session.commit()
    session.close()

    service = MarketDataQualityService(test_settings)
    checked_at = datetime.now(UTC)

    # First run
    result1 = service.evaluate_markets(checked_at=checked_at, market_limit=10)
    assert result1["created"] == 1

    # Second run with same checked_at should skip
    result2 = service.evaluate_markets(checked_at=checked_at, market_limit=10)
    assert result2["created"] == 0
    assert result2["skipped_existing"] == 1


def test_evaluate_markets_skips_active_markets_after_close_time(test_db, test_settings, monkeypatch):
    import services.dq.service as dq_service_module

    def mock_session_scope():
        from contextlib import contextmanager

        @contextmanager
        def _scope():
            s = test_db()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        return _scope()

    monkeypatch.setattr(dq_service_module, "session_scope", mock_session_scope)

    session = test_db()
    expired_market = Market(
        market_id="expired_active_market",
        question="expired active market",
        description="expired active market",
        market_status="active_accepting_orders",
        outcomes=["Yes", "No"],
        clob_token_ids=["expired_yes", "expired_no"],
        close_time=datetime(2026, 4, 10, 7, 0, tzinfo=UTC),
    )
    live_market = Market(
        market_id="live_active_market",
        question="live active market",
        description="live active market",
        market_status="active_accepting_orders",
        outcomes=["Yes", "No"],
        clob_token_ids=["live_yes", "live_no"],
        close_time=datetime(2026, 4, 10, 9, 0, tzinfo=UTC),
    )
    session.add_all([expired_market, live_market])
    session.commit()

    session.add_all(
        [
            MarketSnapshot(
                market_ref_id=expired_market.id,
                snapshot_time=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
                best_bid_no=Decimal("0.45"),
                best_ask_no=Decimal("0.55"),
                best_bid_yes=Decimal("0.45"),
                best_ask_yes=Decimal("0.55"),
                spread=Decimal("0.10"),
                top_of_book_depth=Decimal("1000"),
                cumulative_depth_at_target_size=Decimal("500"),
                traded_volume=Decimal("10000"),
            ),
            MarketSnapshot(
                market_ref_id=live_market.id,
                snapshot_time=datetime(2026, 4, 10, 8, 0, tzinfo=UTC),
                best_bid_no=Decimal("0.45"),
                best_ask_no=Decimal("0.55"),
                best_bid_yes=Decimal("0.45"),
                best_ask_yes=Decimal("0.55"),
                spread=Decimal("0.10"),
                top_of_book_depth=Decimal("1000"),
                cumulative_depth_at_target_size=Decimal("500"),
                traded_volume=Decimal("10000"),
            ),
        ]
    )
    session.commit()
    session.close()

    service = MarketDataQualityService(test_settings)
    checked_at = datetime(2026, 4, 10, 8, 5, tzinfo=UTC)
    result = service.evaluate_markets(checked_at=checked_at, market_limit=10)

    assert result["selected_markets"] == 1
    assert result["created"] == 1

    session = test_db()
    results = session.query(DataQualityResult).all()
    assert len(results) == 1
    saved_market = session.query(Market).filter(Market.id == results[0].market_ref_id).one()
    assert saved_market.market_id == "live_active_market"
    session.close()
