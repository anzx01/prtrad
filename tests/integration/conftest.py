"""Integration test fixtures for API testing."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

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
from sqlalchemy.orm import close_all_sessions, sessionmaker

from db.base import Base
from db import models  # noqa: F401 - Import models to register them with Base
from db.session import get_db
from app.main import app


# Configure a session factory that will be rebound to a per-test engine.
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False)
test_engine = None


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
def setup_test_database(tmp_path):
    """Create a fresh SQLite database for each integration test."""
    global test_engine

    close_all_sessions()
    if test_engine is not None:
        test_engine.dispose()

    test_db_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    TestSessionLocal.configure(bind=test_engine)
    Base.metadata.create_all(test_engine)
    yield

    close_all_sessions()
    app.dependency_overrides.clear()
    if test_engine is not None:
        test_engine.dispose()
        test_engine = None


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
