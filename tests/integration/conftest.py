"""Integration test fixtures for API testing."""
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add apps/api to sys.path before importing app modules
api_path = Path(__file__).parent.parent.parent / "apps" / "api"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from db import models  # noqa: F401 - Import models to register them with Base
from db.session import get_db
from app.main import app


# Create test engine with file-based database for sharing across connections
test_db_path = Path(__file__).parent / "test.db"
test_engine = create_engine(
    f"sqlite:///{test_db_path}",
    echo=False,
)

# Create test session factory
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override get_db dependency to use test database."""
    session = TestSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Mock audit service to avoid database issues in tests
class MockAuditLogService:
    """Mock audit service that doesn't write to database."""

    def write_event(self, event, session=None):
        """Mock write_event - does nothing."""
        return "mock-audit-id"

    def safe_write_event(self, event, session=None, *, context=None):
        """Mock safe_write_event - does nothing."""
        return "mock-audit-id"

    def log(self, **kwargs):
        """Mock log - does nothing."""
        return "mock-audit-id"


@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """Create all tables in the test database before each test."""
    # Remove old test database if exists
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except PermissionError:
            pass  # File is locked, will be overwritten

    # Create all tables
    Base.metadata.create_all(test_engine)
    yield

    # Close all connections
    test_engine.dispose()

    # Clean up after test
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except PermissionError:
            pass  # File is locked, will be cleaned up later


@pytest.fixture(scope="function")
def client():
    """Create a test client using FastAPI dependency override."""
    app.dependency_overrides[get_db] = override_get_db

    # Mock audit service globally
    mock_audit = MockAuditLogService()
    with patch('middleware.request_context.get_audit_log_service', return_value=mock_audit):
        with patch('services.audit.get_audit_log_service', return_value=mock_audit):
            with TestClient(app) as test_client:
                yield test_client

    app.dependency_overrides.clear()
