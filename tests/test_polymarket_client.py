"""
Unit tests for Polymarket API clients.
"""
import pytest
from unittest.mock import Mock, patch
import httpx

from apps.api.services.ingest.polymarket_client import (
    PolymarketApiError,
    PolymarketGammaClient,
    PolymarketClobClient,
)


def test_gamma_client_initialization():
    """Test Gamma client initializes correctly."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15
    )
    assert client._client.base_url == "https://gamma-api.polymarket.com"


def test_gamma_client_list_events_success():
    """Test successful event listing."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15
    )

    mock_response = Mock()
    mock_response.json.return_value = [
        {"id": "1", "title": "Test Event", "markets": []}
    ]
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        events = client.list_events(
            limit=10,
            offset=0,
            active=True,
            closed=False,
            archived=False
        )

    assert len(events) == 1
    assert events[0]["id"] == "1"


def test_gamma_client_list_events_http_error():
    """Test HTTP error handling."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15
    )

    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error",
        request=Mock(),
        response=mock_response
    )

    with patch.object(client._client, "get", return_value=mock_response):
        with pytest.raises(PolymarketApiError, match="Gamma API error: 500"):
            client.list_events(
                limit=10,
                offset=0,
                active=True,
                closed=False,
                archived=False
            )


def test_gamma_client_list_events_invalid_response():
    """Test invalid response format handling."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15
    )

    mock_response = Mock()
    mock_response.json.return_value = {"error": "Invalid format"}
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response):
        with pytest.raises(PolymarketApiError, match="返回结构不是数组"):
            client.list_events(
                limit=10,
                offset=0,
                active=True,
                closed=False,
                archived=False
            )


def test_clob_client_initialization():
    """Test CLOB client initializes correctly."""
    client = PolymarketClobClient(
        base_url="https://clob.polymarket.com",
        timeout_seconds=15
    )
    assert client._client.base_url == "https://clob.polymarket.com"


def test_clob_client_get_order_books_success():
    """Test successful order book retrieval."""
    client = PolymarketClobClient(
        base_url="https://clob.polymarket.com",
        timeout_seconds=15
    )

    mock_response = Mock()
    mock_response.json.return_value = [
        {"asset_id": "token1", "bids": [], "asks": []}
    ]
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "post", return_value=mock_response):
        books = client.get_order_books(["token1"])

    assert len(books) == 1
    assert books[0]["asset_id"] == "token1"


def test_clob_client_get_order_books_empty():
    """Test order book retrieval with empty token list."""
    client = PolymarketClobClient(
        base_url="https://clob.polymarket.com",
        timeout_seconds=15
    )

    books = client.get_order_books([])
    assert books == []


def test_clob_client_retry_on_failure():
    """Test that HTTP client retries on failure."""
    client = PolymarketClobClient(
        base_url="https://clob.polymarket.com",
        timeout_seconds=15
    )

    # The client should have retry transport configured
    assert client._client._transport._pool._retries == 3
