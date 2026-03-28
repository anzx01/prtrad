from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


settings = get_settings()

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_session() -> Session:
    return SessionLocal()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
