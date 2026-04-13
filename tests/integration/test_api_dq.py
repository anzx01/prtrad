"""Integration tests for DQ API endpoints."""
from datetime import UTC, datetime
from decimal import Decimal
import uuid

from db.models import AuditLog, DataQualityResult, Market, MarketSnapshot


def test_get_dq_summary_empty(client):
    response = client.get("/dq/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_checks"] == 0
    assert data["summary"]["status_distribution"] == {}
    assert data["summary"]["top_blocking_reasons"] == []
    assert data["summary"]["latest_snapshot_capture"] is None
    assert data["recent_results"] == []


def test_get_dq_summary_with_data(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    checked_at = datetime.now(UTC)
    try:
        markets = [
            Market(
                id=uuid.uuid4(),
                market_id="test-market-pass-1",
                question="Pass market 1?",
                market_status="active_accepting_orders",
                source_updated_at=datetime.now(UTC),
            ),
            Market(
                id=uuid.uuid4(),
                market_id="test-market-pass-2",
                question="Pass market 2?",
                market_status="active_accepting_orders",
                source_updated_at=datetime.now(UTC),
            ),
            Market(
                id=uuid.uuid4(),
                market_id="test-market-warn-1",
                question="Warn market?",
                market_status="active_accepting_orders",
                source_updated_at=datetime.now(UTC),
            ),
            Market(
                id=uuid.uuid4(),
                market_id="test-market-fail-1",
                question="Fail market?",
                market_status="active_accepting_orders",
                source_updated_at=datetime.now(UTC),
            ),
        ]
        session.add_all(markets)
        session.commit()

        results = [
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=markets[0].id,
                checked_at=checked_at,
                status="pass",
                score=Decimal("0.95"),
                failure_count=0,
                result_details={"blocking_reason_codes": []},
                rule_version="v1.0",
            ),
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=markets[1].id,
                checked_at=checked_at,
                status="pass",
                score=Decimal("0.90"),
                failure_count=0,
                result_details={"blocking_reason_codes": []},
                rule_version="v1.0",
            ),
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=markets[2].id,
                checked_at=checked_at,
                status="warn",
                score=Decimal("0.75"),
                failure_count=1,
                result_details={"blocking_reason_codes": []},
                rule_version="v1.0",
            ),
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=markets[3].id,
                checked_at=checked_at,
                status="fail",
                score=Decimal("0.50"),
                failure_count=3,
                result_details={"blocking_reason_codes": ["REJ_DATA_STALE"]},
                rule_version="v1.0",
            ),
        ]
        session.add_all(results)
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/summary")
    assert response.status_code == 200
    data = response.json()

    summary = data["summary"]
    assert summary["total_checks"] == 4
    assert summary["status_distribution"]["pass"] == 2
    assert summary["status_distribution"]["warn"] == 1
    assert summary["status_distribution"]["fail"] == 1
    assert summary["pass_rate"] == 0.5
    assert summary["latest_checked_at"] is not None
    assert summary["top_blocking_reasons"][0]["reason_code"] == "REJ_DATA_STALE"
    assert len(data["recent_results"]) == 4
    assert data["recent_results"][0]["status"] == "fail"
    assert data["recent_results"][0]["market_id"] == "test-market-fail-1"


def test_get_dq_summary_uses_latest_batch_only(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    market = Market(
        id=uuid.uuid4(),
        market_id="batch-market",
        question="Batch market?",
        market_status="active_accepting_orders",
        source_updated_at=datetime.now(UTC),
    )
    session.add(market)
    session.commit()

    old_checked_at = datetime(2026, 1, 1, tzinfo=UTC)
    new_checked_at = datetime(2026, 4, 1, tzinfo=UTC)
    session.add_all(
        [
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=old_checked_at,
                status="fail",
                score=Decimal("0.40"),
                failure_count=2,
                result_details={"blocking_reason_codes": ["REJ_DATA_STALE"]},
                rule_version="v1.0",
            ),
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=new_checked_at,
                status="pass",
                score=Decimal("0.95"),
                failure_count=0,
                result_details={"blocking_reason_codes": []},
                rule_version="v1.1",
            ),
        ]
    )
    session.commit()
    session.close()

    response = client.get("/dq/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_checks"] == 1
    assert data["summary"]["status_distribution"] == {"pass": 1}
    assert data["recent_results"][0]["status"] == "pass"


def test_get_dq_summary_limit(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    checked_at = datetime.now(UTC)
    try:
        markets = [
            Market(
                id=uuid.uuid4(),
                market_id=f"test-market-{index:02d}",
                question=f"Test market {index}?",
                market_status="active_accepting_orders",
                source_updated_at=datetime.now(UTC),
            )
            for index in range(15)
        ]
        session.add_all(markets)
        session.commit()

        results = [
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=checked_at,
                status="pass",
                score=Decimal("0.95"),
                failure_count=0,
                result_details={"blocking_reason_codes": []},
                rule_version="v1.0",
            )
            for market in markets
        ]
        session.add_all(results)
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/summary?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["recent_results"]) == 5


def test_get_dq_summary_includes_snapshot_capture_diagnostics(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    checked_at = datetime(2026, 4, 10, 8, 5, tzinfo=UTC)
    snapshot_time = datetime(2026, 4, 10, 8, 0, tzinfo=UTC)
    try:
        market = Market(
            id=uuid.uuid4(),
            market_id="snapshot-diagnostics-market",
            question="Snapshot diagnostics market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        session.add(market)
        session.commit()

        session.add(
            MarketSnapshot(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                snapshot_time=snapshot_time,
                best_bid_no=Decimal("0.40"),
                best_ask_no=Decimal("0.50"),
            )
        )
        session.add(
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=checked_at,
                status="pass",
                score=Decimal("0.95"),
                failure_count=0,
                result_details={"blocking_reason_codes": []},
                rule_version="v1.0",
            )
        )
        session.add(
            AuditLog(
                id=uuid.uuid4(),
                actor_id="worker.ingest.capture_active_market_snapshots",
                actor_type="system",
                object_type="market_snapshot_capture",
                object_id=snapshot_time.isoformat(),
                action="execute",
                result="success",
                task_id="snapshot-task-1",
                event_payload={
                    "selected_markets": 200,
                    "created": 198,
                    "skipped_existing": 0,
                    "skipped_missing_mapping": 2,
                    "skipped_missing_order_books": 1,
                    "book_fetch_failed_tokens": 3,
                    "created_from_source_payload": 1,
                },
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/summary")
    assert response.status_code == 200
    data = response.json()
    capture = data["summary"]["latest_snapshot_capture"]
    assert capture["task_id"] == "snapshot-task-1"
    assert capture["selected_markets"] == 200
    assert capture["created"] == 198
    assert capture["skipped_missing_mapping"] == 2
    assert capture["book_fetch_failed_tokens"] == 3
    assert capture["created_from_source_payload"] == 1
    assert capture["triggered_at"] == snapshot_time.isoformat()
    assert capture["source_payload_fallback_enabled"] is True


def test_get_market_dq_result(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    try:
        market = Market(
            id=uuid.uuid4(),
            market_id="test-market",
            question="Test market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        session.add(market)
        session.commit()

        dq_result = DataQualityResult(
            id=uuid.uuid4(),
            market_ref_id=market.id,
            checked_at=datetime.now(UTC),
            status="pass",
            score=Decimal("0.95"),
            failure_count=0,
            result_details={"checks": ["spread_check", "volume_check"]},
            rule_version="v1.0",
        )
        session.add(dq_result)
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/markets/test-market")
    assert response.status_code == 200
    data = response.json()
    result = data["result"]
    assert result["status"] == "pass"
    assert result["score"] == 0.95
    assert result["failure_count"] == 0
    assert result["rule_version"] == "v1.0"
    assert "checks" in result["result_details"]


def test_get_market_dq_result_market_not_found(client):
    response = client.get("/dq/markets/nonexistent-market")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_market_dq_result_no_result(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    try:
        market = Market(
            id=uuid.uuid4(),
            market_id="test-market",
            question="Test market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        session.add(market)
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/markets/test-market")
    assert response.status_code == 404
    assert "no dq result" in response.json()["detail"].lower()


def test_get_market_dq_result_latest(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    try:
        market = Market(
            id=uuid.uuid4(),
            market_id="test-market",
            question="Test market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        session.add(market)
        session.commit()

        old_result = DataQualityResult(
            id=uuid.uuid4(),
            market_ref_id=market.id,
            checked_at=datetime(2026, 1, 1, tzinfo=UTC),
            status="fail",
            score=Decimal("0.50"),
            failure_count=3,
            rule_version="v1.0",
        )
        new_result = DataQualityResult(
            id=uuid.uuid4(),
            market_ref_id=market.id,
            checked_at=datetime(2026, 4, 1, tzinfo=UTC),
            status="pass",
            score=Decimal("0.95"),
            failure_count=0,
            rule_version="v1.1",
        )
        session.add_all([old_result, new_result])
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/markets/test-market")
    assert response.status_code == 200
    data = response.json()
    result = data["result"]
    assert result["status"] == "pass"
    assert result["rule_version"] == "v1.1"
