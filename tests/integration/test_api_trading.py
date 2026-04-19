from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import ModuleType, SimpleNamespace
import sys
import uuid

from app.config import get_settings
from db.models import (
    BacktestRun,
    DataQualityResult,
    KillSwitchRequest,
    Market,
    MarketClassificationResult,
    MarketSnapshot,
    NetEVCandidate,
    ShadowRun,
    TradingOrderRecord,
)
from tests.integration.conftest import TestSessionLocal
import services.trading.service as trading_service_module


def _seed_trading_ready_market(
    *,
    market_code: str = "trade-ready-1",
    backtest_recommendation: str = "watch",
    shadow_recommendation: str = "watch",
) -> None:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id=market_code,
                question="Will trading control work?",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=2),
                open_time=now - timedelta(days=2),
                close_time=now + timedelta(days=2),
                clob_token_ids=["yes-token-1", "no-token-1"],
                outcomes=["Yes", "No"],
                source_updated_at=now,
            )
        )
        session.add(
            MarketSnapshot(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                snapshot_time=now,
                best_bid_no=Decimal("0.42"),
                best_ask_no=Decimal("0.45"),
                best_bid_yes=Decimal("0.55"),
                best_ask_yes=Decimal("0.58"),
                last_trade_price_no=Decimal("0.44"),
                spread=Decimal("0.03"),
                top_of_book_depth=Decimal("5000"),
                cumulative_depth_at_target_size=Decimal("8000"),
                trade_count=20,
                traded_volume=Decimal("12000"),
                last_trade_age_seconds=30,
            )
        )
        session.add(
            MarketClassificationResult(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                rule_version="tag_default_v2",
                source_fingerprint=f"fp-{market_code}",
                classification_status="Tagged",
                primary_category_code="CAT_POLITICS",
                admission_bucket_code="LIST_WHITE",
                confidence=Decimal("0.98"),
                requires_review=False,
                conflict_count=0,
                failure_reason_code=None,
                result_details={"summary": {"risk_factor_codes": ["RF_MACRO_CORRELATED"]}},
                classified_at=now,
            )
        )
        session.add(
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market_id,
                checked_at=now,
                status="pass",
                score=Decimal("0.99"),
                failure_count=0,
                result_details={"blocking_reason_codes": [], "warning_reason_codes": []},
                rule_version="dq_v1",
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
        session.add(
            BacktestRun(
                id=uuid.uuid4(),
                run_name="bt-watch",
                status="completed",
                recommendation=backtest_recommendation,
                window_start=now - timedelta(days=30),
                window_end=now,
                strategy_version="baseline-v1",
                executed_by="tester",
                parameters={"window_days": 30},
                summary={"totals": {"candidate_count": 1, "admitted_count": 1}},
                completed_at=now,
            )
        )
        session.add(
            ShadowRun(
                id=uuid.uuid4(),
                run_name="shadow-watch",
                risk_state="Normal",
                recommendation=shadow_recommendation,
                executed_by="tester",
                summary={"decision_rationale": []},
                checklist=[],
                completed_at=now,
            )
        )
        session.commit()
    finally:
        session.close()


def _seed_existing_live_order(*, market_code: str = "trade-live-limit") -> None:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id=market_code,
                question="Existing live order market",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=2),
                open_time=now - timedelta(days=2),
                close_time=now + timedelta(days=2),
                clob_token_ids=["yes-token-limit", "no-token-limit"],
                outcomes=["Yes", "No"],
                source_updated_at=now,
            )
        )
        session.add(
            TradingOrderRecord(
                id=uuid.uuid4(),
                trading_runtime_state_id=None,
                market_ref_id=market_id,
                mode="live",
                status="matched",
                provider="polymarket_clob",
                market_id_snapshot=market_code,
                question_snapshot="Existing live order market",
                outcome_side="yes",
                token_id="yes-token-limit",
                order_price=Decimal("0.50"),
                order_size=Decimal("10.000000"),
                notional_amount=Decimal("5.000000"),
                expected_net_ev=Decimal("0.040000"),
                requested_by="tester",
                provider_order_id="existing-live-order",
                failure_reason_code=None,
                failure_reason_text=None,
                execution_details={"simulated": False},
                submitted_at=now,
                completed_at=now,
            )
        )
        session.commit()
    finally:
        session.close()


def _install_fake_live_sdk(
    monkeypatch,
    *,
    balance: str = "1000",
    allowance: str = "1000",
    submit_status: str = "live",
    order_statuses: list[str] | None = None,
    cancel_response: dict | None = None,
):
    fake_module = ModuleType("py_clob_client_v2")
    fake_module.Side = SimpleNamespace(BUY="BUY")
    fake_module.OrderType = SimpleNamespace(GTC="GTC")
    fake_module.AssetType = SimpleNamespace(COLLATERAL="COLLATERAL")

    captured: dict[str, list] = {
        "orders": [],
        "cancel_order_ids": [],
        "get_order_calls": [],
    }
    queued_statuses = list(order_statuses or [])

    class _FakeApiCreds:
        def __init__(self, api_key: str, api_secret: str, api_passphrase: str) -> None:
            self.api_key = api_key
            self.api_secret = api_secret
            self.api_passphrase = api_passphrase

    class _FakeBalanceAllowanceParams:
        def __init__(self, asset_type: str) -> None:
            self.asset_type = asset_type

    class _FakeOrderArgsV2:
        def __init__(self, token_id: str, price: float, size: float, side: str) -> None:
            self.token_id = token_id
            self.price = price
            self.size = size
            self.side = side

    class _FakeOrderPayload:
        def __init__(self, orderID: str) -> None:
            self.orderID = orderID

    class _FakeClobClient:
        def __init__(
            self,
            host,
            chain_id,
            key=None,
            creds=None,
            signature_type=None,
            funder=None,
            use_server_time=False,
            retry_on_error=False,
        ) -> None:
            self.host = host
            self.chain_id = chain_id
            self.key = key
            self.creds = creds
            self.signature_type = signature_type
            self.funder = funder
            self.use_server_time = use_server_time
            self.retry_on_error = retry_on_error

        def create_or_derive_api_key(self):
            return _FakeApiCreds("api-key", "api-secret", "api-passphrase")

        def get_address(self):
            return "0xFunderAddress"

        def update_balance_allowance(self, params):
            return {"ok": True, "asset_type": params.asset_type}

        def get_balance_allowance(self, params):
            return {"balance": balance, "allowance": allowance}

        def create_and_post_order(self, order_args, order_type):
            captured["orders"].append(order_args)
            return {
                "success": True,
                "orderID": "order-live-123",
                "status": submit_status,
            }

        def get_order(self, order_id):
            captured["get_order_calls"].append(order_id)
            status = queued_statuses.pop(0) if queued_statuses else submit_status
            return {"orderID": order_id, "status": status}

        def cancel_order(self, payload):
            captured["cancel_order_ids"].append(payload.orderID)
            return cancel_response or {"success": True, "canceled": [payload.orderID]}

    fake_module.ApiCreds = _FakeApiCreds
    fake_module.BalanceAllowanceParams = _FakeBalanceAllowanceParams
    fake_module.OrderArgsV2 = _FakeOrderArgsV2
    fake_module.OrderPayload = _FakeOrderPayload
    fake_module.ClobClient = _FakeClobClient

    original_module = sys.modules.get("py_clob_client_v2")
    sys.modules["py_clob_client_v2"] = fake_module
    monkeypatch.setattr(
        trading_service_module.importlib.util,
        "find_spec",
        lambda name: object() if name == "py_clob_client_v2" else None,
    )

    def cleanup() -> None:
        if original_module is None:
            sys.modules.pop("py_clob_client_v2", None)
        else:
            sys.modules["py_clob_client_v2"] = original_module

    return captured, cleanup


def test_get_trading_state_defaults_to_stopped(client):
    response = client.get("/trading/state")
    assert response.status_code == 200
    state = response.json()["state"]
    assert state["status"] == "stopped"
    assert state["mode"] == "paper"
    assert state["live_mode_enabled"] is False
    assert state["latest_order"] is None


def test_start_paper_trading_and_execute_order(client):
    _seed_trading_ready_market()

    start_response = client.post(
        "/trading/start",
        json={"mode": "paper", "actor_id": "ops_console"},
    )
    assert start_response.status_code == 200
    state = start_response.json()["state"]
    assert state["status"] == "running"
    assert state["mode"] == "paper"
    assert state["paper"]["ready"] is True
    assert state["executable_market_count"] == 1

    execute_response = client.post(
        "/trading/execute-next",
        json={"actor_id": "ops_console"},
    )
    assert execute_response.status_code == 200
    payload = execute_response.json()
    assert payload["order"]["status"] == "filled"
    assert payload["order"]["mode"] == "paper"
    assert payload["order"]["provider"] == "paper_engine"
    assert payload["order"]["market_id"] == "trade-ready-1"
    assert payload["order"]["outcome_side"] == "yes"
    assert payload["order"]["provider_order_id"].startswith("paper-")
    assert payload["state"]["latest_order"]["id"] == payload["order"]["id"]

    list_response = client.get("/trading/orders?limit=5")
    assert list_response.status_code == 200
    orders = list_response.json()["orders"]
    assert len(orders) == 1
    assert orders[0]["id"] == payload["order"]["id"]


def test_start_live_returns_error_when_private_key_missing(client, monkeypatch):
    monkeypatch.setenv("TRADING_LIVE_MODE_ENABLED", "true")
    get_settings.cache_clear()
    _seed_trading_ready_market(
        market_code="trade-live-1",
        backtest_recommendation="go",
        shadow_recommendation="go",
    )

    try:
        start_response = client.post(
            "/trading/start",
            json={"mode": "live", "actor_id": "ops_console"},
        )
        assert start_response.status_code == 400
        assert start_response.json()["detail"] == "还没配置实盘私钥，请先补齐 `TRADING_LIVE_PRIVATE_KEY`。"
    finally:
        monkeypatch.delenv("TRADING_LIVE_MODE_ENABLED", raising=False)
        get_settings.cache_clear()


def test_execute_next_live_uses_bankroll_fraction_and_polls_to_match(client, monkeypatch):
    monkeypatch.setenv("TRADING_LIVE_MODE_ENABLED", "true")
    monkeypatch.setenv("TRADING_LIVE_PRIVATE_KEY", "0xabc123")
    monkeypatch.setenv("TRADING_LIVE_BANKROLL_FRACTION", "0.02")
    monkeypatch.setenv("TRADING_LIVE_MIN_NOTIONAL", "5")
    monkeypatch.setenv("TRADING_LIVE_MAX_NOTIONAL", "25")
    monkeypatch.setenv("TRADING_LIVE_DAILY_ORDER_LIMIT", "3")
    monkeypatch.setenv("TRADING_LIVE_STATUS_POLL_ATTEMPTS", "2")
    monkeypatch.setenv("TRADING_LIVE_STATUS_POLL_INTERVAL_SECONDS", "0")
    get_settings.cache_clear()
    _seed_trading_ready_market(
        market_code="trade-live-2",
        backtest_recommendation="go",
        shadow_recommendation="go",
    )

    captured, cleanup = _install_fake_live_sdk(monkeypatch, order_statuses=["matched"])

    try:
        start_response = client.post(
            "/trading/start",
            json={"mode": "live", "actor_id": "ops_console"},
        )
        assert start_response.status_code == 200

        execute_response = client.post(
            "/trading/execute-next",
            json={"actor_id": "ops_console"},
        )
        assert execute_response.status_code == 200
        payload = execute_response.json()

        assert payload["order"]["status"] == "matched"
        assert payload["order"]["mode"] == "live"
        assert payload["order"]["provider_order_id"] == "order-live-123"
        assert payload["order"]["failure_reason_code"] is None
        assert payload["order"]["notional"] == 20.0
        assert payload["order"]["size"] == 34.482758
        assert len(captured["orders"]) == 1
        assert captured["orders"][0].token_id == "yes-token-1"
        assert captured["orders"][0].price == 0.58
        assert round(captured["orders"][0].size, 6) == 34.482758
        assert captured["get_order_calls"] == ["order-live-123"]
    finally:
        cleanup()
        monkeypatch.delenv("TRADING_LIVE_MODE_ENABLED", raising=False)
        monkeypatch.delenv("TRADING_LIVE_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("TRADING_LIVE_BANKROLL_FRACTION", raising=False)
        monkeypatch.delenv("TRADING_LIVE_MIN_NOTIONAL", raising=False)
        monkeypatch.delenv("TRADING_LIVE_MAX_NOTIONAL", raising=False)
        monkeypatch.delenv("TRADING_LIVE_DAILY_ORDER_LIMIT", raising=False)
        monkeypatch.delenv("TRADING_LIVE_STATUS_POLL_ATTEMPTS", raising=False)
        monkeypatch.delenv("TRADING_LIVE_STATUS_POLL_INTERVAL_SECONDS", raising=False)
        get_settings.cache_clear()


def test_start_live_is_blocked_when_daily_order_limit_reached(client, monkeypatch):
    monkeypatch.setenv("TRADING_LIVE_MODE_ENABLED", "true")
    monkeypatch.setenv("TRADING_LIVE_PRIVATE_KEY", "0xabc123")
    monkeypatch.setenv("TRADING_LIVE_DAILY_ORDER_LIMIT", "1")
    get_settings.cache_clear()
    _seed_trading_ready_market(
        market_code="trade-live-3",
        backtest_recommendation="go",
        shadow_recommendation="go",
    )
    _seed_existing_live_order()

    captured, cleanup = _install_fake_live_sdk(monkeypatch)

    try:
        start_response = client.post(
            "/trading/start",
            json={"mode": "live", "actor_id": "ops_console"},
        )
        assert start_response.status_code == 400
        assert start_response.json()["detail"] == "今天的实盘发单次数已达到上限（1 笔），系统今天会自动停住。"
        assert captured["orders"] == []
    finally:
        cleanup()
        monkeypatch.delenv("TRADING_LIVE_MODE_ENABLED", raising=False)
        monkeypatch.delenv("TRADING_LIVE_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("TRADING_LIVE_DAILY_ORDER_LIMIT", raising=False)
        get_settings.cache_clear()


def test_execute_next_live_auto_cancels_unfilled_order(client, monkeypatch):
    monkeypatch.setenv("TRADING_LIVE_MODE_ENABLED", "true")
    monkeypatch.setenv("TRADING_LIVE_PRIVATE_KEY", "0xabc123")
    monkeypatch.setenv("TRADING_LIVE_STATUS_POLL_ATTEMPTS", "2")
    monkeypatch.setenv("TRADING_LIVE_STATUS_POLL_INTERVAL_SECONDS", "0")
    get_settings.cache_clear()
    _seed_trading_ready_market(
        market_code="trade-live-4",
        backtest_recommendation="go",
        shadow_recommendation="go",
    )

    captured, cleanup = _install_fake_live_sdk(monkeypatch, order_statuses=["live", "live"])

    try:
        start_response = client.post(
            "/trading/start",
            json={"mode": "live", "actor_id": "ops_console"},
        )
        assert start_response.status_code == 200

        execute_response = client.post(
            "/trading/execute-next",
            json={"actor_id": "ops_console"},
        )
        assert execute_response.status_code == 200
        payload = execute_response.json()

        assert payload["order"]["status"] == "cancelled"
        assert payload["order"]["provider_order_id"] == "order-live-123"
        assert payload["order"]["failure_reason_code"] is None
        assert captured["cancel_order_ids"] == ["order-live-123"]
        assert captured["get_order_calls"] == ["order-live-123", "order-live-123", "order-live-123"]
    finally:
        cleanup()
        monkeypatch.delenv("TRADING_LIVE_MODE_ENABLED", raising=False)
        monkeypatch.delenv("TRADING_LIVE_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("TRADING_LIVE_STATUS_POLL_ATTEMPTS", raising=False)
        monkeypatch.delenv("TRADING_LIVE_STATUS_POLL_INTERVAL_SECONDS", raising=False)
        get_settings.cache_clear()


def test_running_trading_auto_stops_when_kill_switch_pending(client):
    _seed_trading_ready_market()
    start_response = client.post(
        "/trading/start",
        json={"mode": "paper", "actor_id": "ops_console"},
    )
    assert start_response.status_code == 200

    session = TestSessionLocal()
    try:
        session.add(
            KillSwitchRequest(
                id=uuid.uuid4(),
                request_type="freeze",
                target_scope="global",
                requested_by="risk_bot",
                reason="Auto risk freeze",
                status="pending",
            )
        )
        session.commit()
    finally:
        session.close()

    state_response = client.get("/trading/state")
    assert state_response.status_code == 200
    state = state_response.json()["state"]
    assert state["status"] == "stopped"
    assert state["last_stop_was_automatic"] is True
    assert state["last_stop_reason_code"] == "PENDING_KILL_SWITCH"
    assert state["pending_kill_switch_count"] == 1
