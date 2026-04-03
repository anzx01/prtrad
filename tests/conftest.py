"""
Test configuration for pytest.
"""
import sys
from pathlib import Path

# Add apps/api to Python path for imports
api_path = Path(__file__).parent.parent / "apps" / "api"
sys.path.insert(0, str(api_path))

# Import models at module level BEFORE any fixtures run
# This ensures models are only imported once
from db.base import Base
from db import models  # noqa: F401

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")


@pytest.fixture(scope="session")
def test_engine_session():
    """Create engine and schema once per test session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine_session):
    """Create test database session for each test."""
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine_session)

    # Clean all tables before each test
    session = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()

    yield SessionLocal


@pytest.fixture
def test_settings():
    """Create test settings."""
    from app.config import Settings

    return Settings(
        database_url="sqlite:///:memory:",
        rule_version="test_v1",
    )
