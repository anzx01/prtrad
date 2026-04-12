from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

from app.config import Settings
from db.models import Market
from services.ingest.service import PolymarketIngestService


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


def _event_payload(
    *,
    event_id: str,
    market_id: str,
    question: str,
    active: bool,
    closed: bool,
    updated_at: str,
    uma_resolution_status: str | None = None,
    final_resolution: str | None = None,
    outcome_prices: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": event_id,
        "title": "Test Event",
        "updatedAt": updated_at,
        "tags": [{"id": "tag-1", "label": "Politics", "slug": "politics"}],
        "markets": [
            {
                "id": market_id,
                "question": question,
                "conditionId": f"cond-{market_id}",
                "active": active,
                "closed": closed,
                "acceptingOrders": active and not closed,
                "archived": False,
                "umaResolutionStatus": uma_resolution_status,
                "finalResolution": final_resolution,
                "outcomes": "[\"Yes\", \"No\"]",
                "outcomePrices": str(outcome_prices or ["0.55", "0.45"]).replace("'", "\""),
                "clobTokenIds": "[\"yes-token\", \"no-token\"]",
                "createdAt": "2026-04-01T00:00:00Z",
                "startDate": "2026-04-02T00:00:00Z",
                "endDate": "2026-04-05T00:00:00Z",
                "closedTime": "2026-04-05T00:10:00Z" if closed else None,
                "umaEndDate": "2026-04-05T00:10:00Z" if closed else None,
                "updatedAt": updated_at,
            }
        ],
    }


class _StubGammaClient:
    def __init__(self, responses: dict[tuple[bool, bool, int], list[dict[str, object]]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def list_events(self, **kwargs):  # noqa: ANN003
        self.calls.append(dict(kwargs))
        return self.responses.get((kwargs["active"], kwargs["closed"], kwargs["offset"]), [])


class _UnusedClobClient:
    def get_order_books(self, token_ids: list[str]):  # noqa: ANN201
        raise AssertionError(f"unexpected order book request: {token_ids}")


def test_sync_markets_imports_recent_closed_markets_and_infers_resolution(test_db, test_settings, monkeypatch):
    _patch_session_scope(monkeypatch, test_db)

    gamma_client = _StubGammaClient(
        {
            (True, False, 0): [
                _event_payload(
                    event_id="evt-active",
                    market_id="market-active",
                    question="Active market?",
                    active=True,
                    closed=False,
                    updated_at="2026-04-11T10:00:00Z",
                )
            ],
            (False, True, 0): [
                _event_payload(
                    event_id="evt-closed",
                    market_id="market-closed",
                    question="Closed market?",
                    active=False,
                    closed=True,
                    updated_at="2026-04-11T11:00:00Z",
                    uma_resolution_status="resolved",
                    outcome_prices=["1", "0"],
                )
            ],
        }
    )
    service = PolymarketIngestService(
        settings=Settings(
            database_url=test_settings.database_url,
            ingest_gamma_page_size=100,
            ingest_closed_market_page_limit=1,
        ),
        gamma_client=gamma_client,
        clob_client=_UnusedClobClient(),
    )

    result = service.sync_markets(triggered_at=datetime(2026, 4, 11, 12, 0, tzinfo=UTC), limit_pages=1)

    assert result["created"] == 2
    assert result["pages"] == 2
    assert any(call["active"] is False and call["closed"] is True for call in gamma_client.calls)

    session = test_db()
    closed_market = session.query(Market).filter_by(market_id="market-closed").one()
    assert closed_market.market_status == "resolved"
    assert closed_market.final_resolution == "yes"
    session.close()


def test_sync_markets_keeps_earlier_active_pages_available_for_inactive_detection(test_db, test_settings, monkeypatch):
    _patch_session_scope(monkeypatch, test_db)

    gamma_client = _StubGammaClient(
        {
            (True, False, 0): [
                _event_payload(
                    event_id="evt-a",
                    market_id="market-a",
                    question="Market A?",
                    active=True,
                    closed=False,
                    updated_at="2026-04-11T10:00:00Z",
                )
            ],
            (True, False, 1): [
                _event_payload(
                    event_id="evt-b",
                    market_id="market-b",
                    question="Market B?",
                    active=True,
                    closed=False,
                    updated_at="2026-04-11T10:05:00Z",
                )
            ],
        }
    )
    service = PolymarketIngestService(
        settings=Settings(
            database_url=test_settings.database_url,
            ingest_gamma_page_size=1,
            ingest_closed_market_page_limit=0,
        ),
        gamma_client=gamma_client,
        clob_client=_UnusedClobClient(),
    )

    result = service.sync_markets(triggered_at=datetime(2026, 4, 11, 12, 30, tzinfo=UTC))

    assert result["created"] == 2
    session = test_db()
    statuses = {
        market.market_id: market.market_status
        for market in session.query(Market).order_by(Market.market_id.asc()).all()
    }
    assert statuses == {
        "market-a": "active_accepting_orders",
        "market-b": "active_accepting_orders",
    }
    session.close()
