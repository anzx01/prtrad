param(
    [switch]$KeepDatabase
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$apiPath = Join-Path $repoRoot "apps/api"
$dbPath = Join-Path $repoRoot "var/e2e-paper-trading.sqlite3"

if (-not $KeepDatabase -and (Test-Path $dbPath)) {
    Remove-Item -LiteralPath $dbPath -Force
}

$env:APP_ENV = "test"
$env:DATABASE_URL = "sqlite:///$($dbPath.Replace('\', '/'))"
$env:PYTHONPATH = "$apiPath;$repoRoot;$env:PYTHONPATH"

$pythonExe = Join-Path $repoRoot ".venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

@'
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from db.base import Base
from db.models import Market, MarketSnapshot, NetEVCandidate
from db.session import get_db


engine = create_engine(__import__("os").environ["DATABASE_URL"], connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)


def override_get_db():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


def seed_market():
    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        session.add(
            Market(
                id=market_id,
                market_id="e2e-paper-1",
                question="Will the paper trading e2e pass?",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=2),
                open_time=now - timedelta(days=2),
                close_time=now + timedelta(days=2),
                clob_token_ids=["yes-token-e2e", "no-token-e2e"],
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


def add_snapshot(market_id):
    session = SessionLocal()
    try:
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
                last_trade_price_no=Decimal("0.500000"),
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


def resolve_market(market_id):
    session = SessionLocal()
    try:
        market = session.get(Market, market_id)
        market.final_resolution = "no"
        market.market_status = "resolved"
        session.commit()
    finally:
        session.close()


market_id = seed_market()
client = TestClient(app)

summary = client.get("/paper-trading/summary")
assert summary.status_code == 200, summary.text
assert summary.json()["summary"]["total_count"] == 0

evaluate = client.post("/paper-trading/evaluate", json={"limit": 10, "strategy_version": "e2e-paper-v1"})
assert evaluate.status_code == 200, evaluate.text
assert evaluate.json()["result"]["created_count"] == 1

positions = client.get("/paper-trading/positions?status=open")
assert positions.status_code == 200, positions.text
assert len(positions.json()["positions"]) == 1

add_snapshot(market_id)
mark = client.post("/paper-trading/mark", json={"auto_close": False})
assert mark.status_code == 200, mark.text
assert mark.json()["summary"]["unrealized_pnl"] == 0.5

resolve_market(market_id)
close = client.post("/paper-trading/mark", json={"auto_close": True})
assert close.status_code == 200, close.text
payload = close.json()
assert payload["summary"]["open_count"] == 0
assert payload["summary"]["closed_count"] == 1
assert payload["summary"]["realized_pnl"] == 5.5
assert payload["summary"]["win_rate"] == 1.0

print("paper trading e2e passed")
print(f"created={evaluate.json()['result']['created_count']}")
print(f"unrealized_after_mark={mark.json()['summary']['unrealized_pnl']}")
print(f"realized_after_close={payload['summary']['realized_pnl']}")
'@ | & $pythonExe -
