"""Integration tests for tagging API endpoints."""
import sys
from pathlib import Path
from unittest.mock import Mock

# Add apps/api to sys.path
api_path = Path(__file__).parent.parent.parent / "apps" / "api"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))

import pytest


@pytest.fixture
def mock_tagging_service(monkeypatch):
    """Mock the tagging service for integration tests."""
    mock_service = Mock()

    # Mock tag definitions
    mock_service.list_tag_definitions.return_value = [
        {
            "tag_key": "category:sports",
            "tag_name": "Sports",
            "description": "Sports-related markets",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
        },
        {
            "tag_key": "category:politics",
            "tag_name": "Politics",
            "description": "Political markets",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
        },
    ]

    # Mock rule versions
    mock_service.list_rule_versions.return_value = [
        {
            "version_code": "v1.1",
            "is_active": True,
            "activated_at": "2026-03-01T00:00:00Z",
            "created_at": "2026-03-01T00:00:00Z",
            "rule_count": 15,
        },
        {
            "version_code": "v1.0",
            "is_active": False,
            "activated_at": "2026-01-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
            "rule_count": 10,
        },
    ]

    # Mock active rule version
    mock_service.get_active_rule_version.return_value = {
        "version_code": "v1.1",
        "is_active": True,
        "activated_at": "2026-03-01T00:00:00Z",
        "created_at": "2026-03-01T00:00:00Z",
        "rule_count": 15,
        "rules": [],
    }

    # Mock specific rule version
    mock_service.get_rule_version.return_value = {
        "version_code": "v1.0",
        "is_active": False,
        "activated_at": "2026-01-01T00:00:00Z",
        "created_at": "2026-01-01T00:00:00Z",
        "rule_count": 10,
        "rules": [],
    }

    # Patch the service getter in the routes module
    from app.routes import tagging as tagging_routes
    monkeypatch.setattr(tagging_routes, "get_tagging_rule_service", lambda: mock_service)

    return mock_service


def test_list_tag_definitions(client, mock_tagging_service):
    """Test listing tag definitions."""
    response = client.get("/tagging/definitions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["definitions"]) == 2
    assert data["total"] == 2
    assert data["definitions"][0]["tag_key"] == "category:sports"
    mock_tagging_service.list_tag_definitions.assert_called_once_with(include_inactive=False)


def test_list_tag_definitions_include_inactive(client, mock_tagging_service):
    """Test listing tag definitions including inactive ones."""
    response = client.get("/tagging/definitions?include_inactive=true")
    assert response.status_code == 200
    mock_tagging_service.list_tag_definitions.assert_called_once_with(include_inactive=True)


def test_list_rule_versions(client, mock_tagging_service):
    """Test listing rule versions."""
    response = client.get("/tagging/versions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["versions"]) == 2
    assert data["total"] == 2
    assert data["versions"][0]["version_code"] == "v1.1"
    assert data["versions"][0]["is_active"] is True
    mock_tagging_service.list_rule_versions.assert_called_once_with(limit=50)


def test_list_rule_versions_with_limit(client, mock_tagging_service):
    """Test listing rule versions with custom limit."""
    response = client.get("/tagging/versions?limit=10")
    assert response.status_code == 200
    mock_tagging_service.list_rule_versions.assert_called_once_with(limit=10)


def test_get_active_rule_version(client, mock_tagging_service):
    """Test getting the active rule version."""
    response = client.get("/tagging/versions/active")
    assert response.status_code == 200
    data = response.json()
    assert data["version"]["version_code"] == "v1.1"
    assert data["version"]["is_active"] is True
    mock_tagging_service.get_active_rule_version.assert_called_once()


def test_get_active_rule_version_not_found(client, mock_tagging_service):
    """Test getting active rule version when none exists."""
    mock_tagging_service.get_active_rule_version.return_value = None

    response = client.get("/tagging/versions/active")
    assert response.status_code == 404
    assert "no active rule version" in response.json()["detail"].lower()


def test_get_rule_version(client, mock_tagging_service):
    """Test getting a specific rule version."""
    response = client.get("/tagging/versions/v1.0")
    assert response.status_code == 200
    data = response.json()
    assert data["version"]["version_code"] == "v1.0"
    assert data["version"]["is_active"] is False
    mock_tagging_service.get_rule_version.assert_called_once_with("v1.0")


def test_get_rule_version_not_found(client, mock_tagging_service):
    """Test getting non-existent rule version."""
    mock_tagging_service.get_rule_version.return_value = None

    response = client.get("/tagging/versions/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
