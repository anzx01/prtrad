from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
import uuid

from app.config import Settings
from db.models import Market, MarketSnapshot
from services.ingest.polymarket_client import PolymarketApiError
from services.ingest.service import PolymarketIngestService


class _DummyGammaClient:
    def list_events(self, **kwargs):  # noqa: ANN003
        return []


def _book(asset_id: str, bid: str, ask: str) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "bids": [{"price": bid, "size": "20"}],
        "asks": [{"price": ask, "size": "30"}],
        "last_trade_price": ask,
    }


class _FlakyClobClient:
    def __init__(self, *, fail_on_multi: bool, permanently_failed_tokens: set[str] | None = None) -> None:
        self.fail_on_multi = fail_on_multi
        self.permanently_failed_tokens = permanently_failed_tokens or set()
        self.calls: list[list[str]] = []

    def get_order_books(self, token_ids: list[str]) -> list[dict[str, object]]:
        self.calls.append(list(token_ids))

        if self.fail_on_multi and len(token_ids) > 1:
            raise PolymarketApiError("CLOB API request failed: timed out")

        token_id = token_ids[0]
        if token_id in self.permanently_failed_tokens:
            raise PolymarketApiError("CLOB API request failed: timed out")

        if token_id.startswith("yes"):
            return [_book(token_id, "0.45", "0.55")]
        return [_book(token_id, "0.40", "0.60")]


def _patch_session_scope(monkeypatch, test_db) -> None:
    import services.ingest.service as ingest_service_module

    def _mock_session_scope():
        @contextmanager
        def _scope():
            session = test_db()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        return _scope()

    monkeypatch.setattr(ingest_service_module, "session_scope", _mock_session_scope)


def _seed_active_markets(test_db) -> tuple[uuid.UUID, uuid.UUID]:
    session = test_db()
    market_a = Market(
        id=uuid.uuid4(),
        market_id="snapshot-test-a",
        question="snapshot test a",
        market_status="active_accepting_orders",
        outcomes=["Yes", "No"],
        clob_token_ids=["yes-a", "no-a"],
        source_updated_at=datetime.now(UTC),
        source_payload={"market": {"volume_24hr_clob": "123.4"}},
    )
    market_b = Market(
        id=uuid.uuid4(),
        market_id="snapshot-test-b",
        question="snapshot test b",
        market_status="active_accepting_orders",
        outcomes=["Yes", "No"],
        clob_token_ids=["yes-b", "no-b"],
        source_updated_at=datetime.now(UTC),
        source_payload={"market": {"volume_24hr_clob": "88.8"}},
    )
    session.add_all([market_a, market_b])
    session.commit()
    market_ids = (market_a.id, market_b.id)
    session.close()
    return market_ids


def test_capture_snapshots_recovers_from_failed_large_batch(test_db, test_settings, monkeypatch):
    _patch_session_scope(monkeypatch, test_db)
    market_a_id, market_b_id = _seed_active_markets(test_db)

    clob_client = _FlakyClobClient(fail_on_multi=True)
    service = PolymarketIngestService(
        settings=Settings(
            database_url=test_settings.database_url,
            ingest_clob_batch_size=4,
            ingest_snapshot_market_limit=200,
            ingest_allow_source_payload_fallback=False,
        ),
        gamma_client=_DummyGammaClient(),
        clob_client=clob_client,
    )

    triggered_at = datetime(2026, 4, 10, 7, 30, tzinfo=UTC)
    result = service.capture_snapshots(triggered_at=triggered_at)

    assert result["selected_markets"] == 2
    assert result["created"] == 2
    assert result["book_fetch_failed_tokens"] == 0
    assert result["skipped_missing_order_books"] == 0
    assert any(len(call) == 4 for call in clob_client.calls)
    assert any(len(call) == 1 for call in clob_client.calls)

    session = test_db()
    snapshots = session.query(MarketSnapshot).all()
    assert len(snapshots) == 2
    snapshot_market_ids = {snapshot.market_ref_id for snapshot in snapshots}
    assert snapshot_market_ids == {market_a_id, market_b_id}
    session.close()


def test_capture_snapshots_keeps_partial_success_when_single_token_fails(test_db, test_settings, monkeypatch):
    _patch_session_scope(monkeypatch, test_db)
    _seed_active_markets(test_db)

    clob_client = _FlakyClobClient(
        fail_on_multi=True,
        permanently_failed_tokens={"yes-b"},
    )
    service = PolymarketIngestService(
        settings=Settings(
            database_url=test_settings.database_url,
            ingest_clob_batch_size=4,
            ingest_snapshot_market_limit=200,
            ingest_allow_source_payload_fallback=False,
        ),
        gamma_client=_DummyGammaClient(),
        clob_client=clob_client,
    )

    triggered_at = datetime(2026, 4, 10, 7, 45, tzinfo=UTC)
    result = service.capture_snapshots(triggered_at=triggered_at)

    assert result["selected_markets"] == 2
    assert result["created"] == 1
    assert result["book_fetch_failed_tokens"] == 1
    assert result["skipped_missing_order_books"] == 1

    session = test_db()
    snapshots = session.query(MarketSnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_time == triggered_at.replace(tzinfo=None)
    assert snapshots[0].best_bid_no == Decimal("0.40")
    session.close()


def test_capture_snapshots_falls_back_to_source_payload_when_books_unavailable(test_db, test_settings, monkeypatch):
    _patch_session_scope(monkeypatch, test_db)

    session = test_db()
    market = Market(
        id=uuid.uuid4(),
        market_id="snapshot-fallback-a",
        question="snapshot fallback a",
        market_status="active_accepting_orders",
        outcomes=["Yes", "No"],
        clob_token_ids=["yes-fallback-a", "no-fallback-a"],
        source_updated_at=datetime.now(UTC),
        source_payload={
            "market": {
                "best_bid": "0.42",
                "best_ask": "0.58",
                "spread": "0.16",
                "liquidity_clob": "50",
                "volume_24hr_clob": "12.5",
                "last_trade_price": "0.40",
            }
        },
    )
    session.add(market)
    session.commit()
    market_id = market.id
    session.close()

    clob_client = _FlakyClobClient(fail_on_multi=True)
    service = PolymarketIngestService(
        settings=Settings(
            database_url=test_settings.database_url,
            ingest_clob_batch_size=4,
            ingest_snapshot_market_limit=200,
            ingest_allow_source_payload_fallback=True,
        ),
        gamma_client=_DummyGammaClient(),
        clob_client=clob_client,
    )

    triggered_at = datetime(2026, 4, 10, 8, 0, tzinfo=UTC)
    result = service.capture_snapshots(triggered_at=triggered_at)

    assert result["selected_markets"] == 1
    assert result["created"] == 1
    assert result["created_from_source_payload"] == 1
    assert result["book_fetch_failed_tokens"] == 2
    assert result["skipped_missing_order_books"] == 0

    session = test_db()
    snapshots = session.query(MarketSnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].market_ref_id == market_id
    assert snapshots[0].best_bid_yes == Decimal("0.42")
    assert snapshots[0].best_ask_yes == Decimal("0.58")
    assert snapshots[0].best_bid_no == Decimal("0.42")
    assert snapshots[0].best_ask_no == Decimal("0.58")
    assert snapshots[0].top_of_book_depth == Decimal("50")
    assert snapshots[0].cumulative_depth_at_target_size == Decimal("50")
    session.close()
