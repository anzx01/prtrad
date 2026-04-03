"""Integration tests for markets API endpoints."""
from datetime import UTC, datetime
from decimal import Decimal
import uuid

from db.models import Market, MarketSnapshot, DataQualityResult


def test_list_markets_empty(client):
    """Test listing markets when database is empty."""
    response = client.get("/markets")
    assert response.status_code == 200
    data = response.json()
    assert data["markets"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["has_more"] is False


def test_list_markets_with_data(client):
    """Test listing markets with sample data."""
    from tests.integration.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        # Create test markets
        market1 = Market(
            id=uuid.uuid4(),
            market_id="test-market-1",
            question="Will it rain tomorrow?",
            description="Test market 1",
            market_status="active_accepting_orders",
            category_raw="Weather",
            close_time=datetime(2026, 12, 31, tzinfo=UTC),
            source_updated_at=datetime.now(UTC),
        )
        market2 = Market(
            id=uuid.uuid4(),
            market_id="test-market-2",
            question="Will the sun rise?",
            description="Test market 2",
            market_status="closed",
            category_raw="Astronomy",
            close_time=datetime(2026, 6, 30, tzinfo=UTC),
            source_updated_at=datetime.now(UTC),
        )
        session.add_all([market1, market2])
        session.commit()
    finally:
        session.close()

    response = client.get("/markets")
    assert response.status_code == 200
    data = response.json()
    assert len(data["markets"]) == 2
    assert data["total"] == 2
    assert data["has_more"] is False


def test_list_markets_pagination(client):
    """Test markets pagination."""
    from tests.integration.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        # Create 25 test markets
        markets = [
            Market(
                id=uuid.uuid4(),
                market_id=f"test-market-{i}",
                question=f"Test question {i}?",
                market_status="active_accepting_orders",
                source_updated_at=datetime.now(UTC),
            )
            for i in range(25)
        ]
        session.add_all(markets)
        session.commit()
    finally:
        session.close()

    # First page
    response = client.get("/markets?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["markets"]) == 10
    assert data["total"] == 25
    assert data["has_more"] is True

    # Second page
    response = client.get("/markets?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["markets"]) == 10
    assert data["has_more"] is True

    # Third page
    response = client.get("/markets?page=3&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["markets"]) == 5
    assert data["has_more"] is False


def test_list_markets_filter_by_status(client):
    """Test filtering markets by status."""
    from tests.integration.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        market1 = Market(
            id=uuid.uuid4(),
            market_id="active-market",
            question="Active market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        market2 = Market(
            id=uuid.uuid4(),
            market_id="closed-market",
            question="Closed market?",
            market_status="closed",
            source_updated_at=datetime.now(UTC),
        )
        session.add_all([market1, market2])
        session.commit()
    finally:
        session.close()

    response = client.get("/markets?status=active_accepting_orders")
    assert response.status_code == 200
    data = response.json()
    assert len(data["markets"]) == 1
    assert data["markets"][0]["market_status"] == "active_accepting_orders"


def test_list_markets_search(client):
    """Test searching markets by question text."""
    from tests.integration.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        market1 = Market(
            id=uuid.uuid4(),
            market_id="rain-market",
            question="Will it rain tomorrow?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        market2 = Market(
            id=uuid.uuid4(),
            market_id="sun-market",
            question="Will the sun shine?",
            market_status="active_accepting_orders",
            source_updated_at=datetime.now(UTC),
        )
        session.add_all([market1, market2])
        session.commit()
    finally:
        session.close()

    response = client.get("/markets?search=rain")
    assert response.status_code == 200
    data = response.json()
    assert len(data["markets"]) == 1
    assert "rain" in data["markets"][0]["question"].lower()


def test_get_market_detail(client):
    """Test getting market detail with snapshot and DQ result."""
    from tests.integration.conftest import TestSessionLocal
    session = TestSessionLocal()
    try:
        market = Market(
            id=uuid.uuid4(),
            market_id="detail-market",
            question="Test market detail?",
            description="Detailed test market",
            market_status="active_accepting_orders",
            category_raw="Test",
            source_updated_at=datetime.now(UTC),
        )
        session.add(market)
        session.commit()

        # Add snapshot
        snapshot = MarketSnapshot(
            id=uuid.uuid4(),
            market_ref_id=market.id,
            snapshot_time=datetime.now(UTC),
            best_bid_no=Decimal("0.45"),
            best_ask_no=Decimal("0.55"),
            spread=Decimal("0.10"),
        )
        session.add(snapshot)

        # Add DQ result
        dq_result = DataQualityResult(
            id=uuid.uuid4(),
            market_ref_id=market.id,
            checked_at=datetime.now(UTC),
            status="pass",
            score=Decimal("0.95"),
            failure_count=0,
            rule_version="v1.0",
        )
        session.add(dq_result)
        session.commit()
    finally:
        session.close()

    response = client.get("/markets/detail-market")
    assert response.status_code == 200
    data = response.json()
    assert data["market"]["market_id"] == "detail-market"
    assert data["latest_snapshot"] is not None
    assert data["latest_snapshot"]["best_bid_no"] == 0.45
    assert data["latest_dq_result"] is not None
    assert data["latest_dq_result"]["status"] == "pass"


def test_get_market_detail_not_found(client):
    """Test getting non-existent market."""
    response = client.get("/markets/nonexistent-market")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
