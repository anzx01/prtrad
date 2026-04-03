from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


settings = get_settings()

# Configure connection pool for better performance and resource management
# SQLite doesn't support pool parameters, so we conditionally apply them
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        future=True,
        connect_args={"check_same_thread": False},  # Allow SQLite to be used across threads
    )
else:
    engine = create_engine(
        settings.database_url,
        future=True,
        pool_size=10,  # Number of connections to keep open
        max_overflow=20,  # Additional connections when pool is exhausted
        pool_timeout=30,  # Seconds to wait for a connection
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_session() -> Session:
    """Get a new database session. Caller is responsible for closing it."""
    return SessionLocal()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Session:
    """FastAPI dependency for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
