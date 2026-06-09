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


def test_gamma_client_list_markets_success():
    """Test successful market listing."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15
    )

    mock_response = Mock()
    mock_response.json.return_value = [
        {"id": "market-1", "question": "Test Market"}
    ]
    mock_response.raise_for_status = Mock()

    with patch.object(client._client, "get", return_value=mock_response) as mock_get:
        markets = client.list_markets(
            limit=20,
            offset=0,
            active=True,
            closed=False,
            archived=False,
        )

    assert len(markets) == 1
    assert markets[0]["id"] == "market-1"
    assert mock_get.call_args.kwargs["params"]["limit"] == 20
    assert mock_get.call_args.kwargs["params"]["offset"] == 0


def test_gamma_client_list_events_http_error():
    """Test HTTP error handling."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15,
        retry_max_attempts=1,
    )

    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.headers = {}
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


def test_gamma_client_ignores_invalid_retry_after_header():
    """Test invalid Retry-After header falls back to exponential delay."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15,
        retry_max_attempts=2,
        retry_base_delay_seconds=0.5,
        retry_max_delay_seconds=5.0,
    )

    retry_response = Mock()
    retry_response.status_code = 429
    retry_response.headers = {"Retry-After": "later"}
    retry_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Too many requests",
        request=Mock(),
        response=retry_response,
    )

    success_response = Mock()
    success_response.raise_for_status = Mock()
    success_response.json.return_value = [{"id": "1", "title": "Recovered", "markets": []}]

    with patch.object(client._client, "get", side_effect=[retry_response, success_response]):
        with patch("apps.api.services.ingest.polymarket_client.time.sleep") as mock_sleep:
            client.list_events(
                limit=10,
                offset=0,
                active=True,
                closed=False,
                archived=False,
            )

    mock_sleep.assert_called_once_with(0.5)


def test_gamma_client_retries_on_429_and_succeeds():
    """Test 429 responses are retried with backoff."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15,
        retry_max_attempts=3,
        retry_base_delay_seconds=0.5,
        retry_max_delay_seconds=2.0,
    )

    retry_response = Mock()
    retry_response.status_code = 429
    retry_response.headers = {}
    retry_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Too many requests",
        request=Mock(),
        response=retry_response,
    )

    success_response = Mock()
    success_response.raise_for_status = Mock()
    success_response.json.return_value = [{"id": "1", "title": "Recovered", "markets": []}]

    with patch.object(client._client, "get", side_effect=[retry_response, success_response]) as mock_get:
        with patch("apps.api.services.ingest.polymarket_client.time.sleep") as mock_sleep:
            events = client.list_events(
                limit=10,
                offset=0,
                active=True,
                closed=False,
                archived=False,
            )

    assert len(events) == 1
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(0.5)


def test_gamma_client_prefers_retry_after_header():
    """Test Retry-After header overrides exponential delay."""
    client = PolymarketGammaClient(
        base_url="https://gamma-api.polymarket.com",
        timeout_seconds=15,
        retry_max_attempts=2,
        retry_base_delay_seconds=0.5,
        retry_max_delay_seconds=5.0,
    )

    retry_response = Mock()
    retry_response.status_code = 429
    retry_response.headers = {"Retry-After": "1.5"}
    retry_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Too many requests",
        request=Mock(),
        response=retry_response,
    )

    success_response = Mock()
    success_response.raise_for_status = Mock()
    success_response.json.return_value = [{"id": "1", "title": "Recovered", "markets": []}]

    with patch.object(client._client, "get", side_effect=[retry_response, success_response]):
        with patch("apps.api.services.ingest.polymarket_client.time.sleep") as mock_sleep:
            client.list_events(
                limit=10,
                offset=0,
                active=True,
                closed=False,
                archived=False,
            )

    mock_sleep.assert_called_once_with(1.5)


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
