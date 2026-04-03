"""Integration tests for DQ API endpoints."""
from datetime import UTC, datetime
from decimal import Decimal
import uuid

from db.models import Market, DataQualityResult


def test_get_dq_summary_empty(client):
    """Test DQ summary when no results exist."""
    response = client.get("/dq/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_checks"] == 0
    assert data["summary"]["status_distribution"] == {}
    assert data["recent_results"] == []


def test_get_dq_summary_with_data(client):
    """Test DQ summary with sample data."""
    from tests.integration.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        # Create test market
        market = Market(
            id=uuid.uuid4(),
            market_id="test-market",
            question="Test market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        session.add(market)
        session.commit()

        # Create DQ results with different statuses
        results = [
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=datetime.now(UTC),
                status="pass",
                score=Decimal("0.95"),
                failure_count=0,
                rule_version="v1.0",
            ),
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=datetime.now(UTC),
                status="pass",
                score=Decimal("0.90"),
                failure_count=0,
                rule_version="v1.0",
            ),
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=datetime.now(UTC),
                status="warn",
                score=Decimal("0.75"),
                failure_count=1,
                rule_version="v1.0",
            ),
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=datetime.now(UTC),
                status="fail",
                score=Decimal("0.50"),
                failure_count=3,
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

    # Check summary
    summary = data["summary"]
    assert summary["total_checks"] == 4
    assert summary["status_distribution"]["pass"] == 2
    assert summary["status_distribution"]["warn"] == 1
    assert summary["status_distribution"]["fail"] == 1
    assert summary["pass_rate"] == 0.5  # 2 out of 4

    # Check recent results
    assert len(data["recent_results"]) == 4


def test_get_dq_summary_limit(client):
    """Test DQ summary with limit parameter."""
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

        # Create 15 DQ results
        results = [
            DataQualityResult(
                id=uuid.uuid4(),
                market_ref_id=market.id,
                checked_at=datetime.now(UTC),
                status="pass",
                score=Decimal("0.95"),
                failure_count=0,
                rule_version="v1.0",
            )
            for _ in range(15)
        ]
        session.add_all(results)
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/summary?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["recent_results"]) == 5


def test_get_market_dq_result(client):
    """Test getting DQ result for a specific market."""
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

        # Create DQ result
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
    """Test getting DQ result for non-existent market."""
    response = client.get("/dq/markets/nonexistent-market")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_market_dq_result_no_result(client):
    """Test getting DQ result when market exists but has no results."""
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
    """Test that only the latest DQ result is returned."""
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

        # Create multiple DQ results
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
    # Should return the newer result
    assert result["status"] == "pass"
    assert result["rule_version"] == "v1.1"
