"""
Unit tests for audit log service.
"""
import sqlite3
import uuid
from unittest.mock import Mock

from sqlalchemy.exc import OperationalError

from db.models import AuditLog
from services.audit.service import AuditLogService
from services.audit.contracts import AuditEvent


def _build_sqlite_locked_error() -> OperationalError:
    return OperationalError(
        "INSERT INTO audit_logs (...) VALUES (...)",
        {},
        sqlite3.OperationalError("database is locked"),
    )


def test_audit_service_write_event_with_session(test_db):
    """Test writing audit event with provided session."""
    service = AuditLogService()
    session = test_db()

    event = AuditEvent(
        actor_id="test_user",
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
        request_id="req_123",
    )

    # Write event with provided session
    audit_id = service.write_event(event, session=session)
    assert audit_id is not None

    # Verify the event was written
    audit_log = session.query(AuditLog).filter_by(id=uuid.UUID(audit_id)).first()
    assert audit_log is not None
    assert audit_log.actor_id == "test_user"
    assert audit_log.action == "test_action"

    session.close()


def test_audit_service_write_event_without_session(test_db, monkeypatch):
    """Test writing audit event without provided session."""
    import services.audit.service as audit_service_module

    def mock_session_scope():
        from contextlib import contextmanager

        @contextmanager
        def _scope():
            s = test_db()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        return _scope()

    monkeypatch.setattr(audit_service_module, "session_scope", mock_session_scope)

    service = AuditLogService()
    event = AuditEvent(
        actor_id="test_user",
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
    )

    # Write event without session (creates new session)
    audit_id = service.write_event(event)
    assert audit_id is not None


def test_audit_service_safe_write_event_success(test_db):
    """Test safe write event succeeds."""
    service = AuditLogService()
    session = test_db()

    event = AuditEvent(
        actor_id="test_user",
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
    )

    audit_id = service.safe_write_event(event, session=session)
    assert audit_id is not None

    session.close()


def test_audit_service_safe_write_event_retries_sqlite_lock_without_session(monkeypatch):
    """Test safe write event retries SQLite lock errors for independent writes."""
    import services.audit.service as audit_service_module

    service = AuditLogService()
    event = AuditEvent(
        actor_id="test_user",
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
    )

    sleep_calls: list[float] = []
    write_event = Mock(side_effect=[_build_sqlite_locked_error(), "audit-123"])

    monkeypatch.setattr(audit_service_module.time, "sleep", lambda delay: sleep_calls.append(delay))
    monkeypatch.setattr(service, "write_event", write_event)

    audit_id = service.safe_write_event(event)

    assert audit_id == "audit-123"
    assert write_event.call_count == 2
    assert sleep_calls == [audit_service_module._SQLITE_LOCK_RETRY_DELAYS[0]]
    assert [call.kwargs["session"] for call in write_event.call_args_list] == [None, None]


def test_audit_service_safe_write_event_returns_none_after_sqlite_lock_retries(monkeypatch):
    """Test safe write event gives up after bounded SQLite lock retries."""
    import services.audit.service as audit_service_module

    service = AuditLogService()
    event = AuditEvent(
        actor_id="test_user",
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
    )

    sleep_calls: list[float] = []

    def always_locked(*args, **kwargs):
        raise _build_sqlite_locked_error()

    write_event = Mock(side_effect=always_locked)

    monkeypatch.setattr(audit_service_module.time, "sleep", lambda delay: sleep_calls.append(delay))
    monkeypatch.setattr(service, "write_event", write_event)

    audit_id = service.safe_write_event(event)

    assert audit_id is None
    assert write_event.call_count == len(audit_service_module._SQLITE_LOCK_RETRY_DELAYS) + 1
    assert sleep_calls == list(audit_service_module._SQLITE_LOCK_RETRY_DELAYS)


def test_audit_service_safe_write_event_failure(test_db):
    """Test safe write event handles failures gracefully."""
    service = AuditLogService()

    # Create an invalid event that will cause an error
    event = AuditEvent(
        actor_id="x" * 200,  # Exceeds max length after clipping
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
    )

    # Mock session that raises an error
    mock_session = Mock()
    mock_session.add.side_effect = Exception("Database error")

    # Should return None instead of raising
    audit_id = service.safe_write_event(event, session=mock_session)
    assert audit_id is None


def test_audit_service_safe_write_event_does_not_retry_existing_session_sqlite_lock(monkeypatch):
    """Test safe write event does not retry when caller session is already in use."""
    import services.audit.service as audit_service_module

    service = AuditLogService()
    event = AuditEvent(
        actor_id="test_user",
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
    )

    sleep_calls: list[float] = []
    mock_session = Mock()
    mock_session.add.side_effect = _build_sqlite_locked_error()

    monkeypatch.setattr(audit_service_module.time, "sleep", lambda delay: sleep_calls.append(delay))

    audit_id = service.safe_write_event(event, session=mock_session)

    assert audit_id is None
    assert mock_session.add.call_count == 1
    assert sleep_calls == []


def test_audit_service_clips_long_values(test_db):
    """Test that long values are clipped to max length."""
    service = AuditLogService()
    session = test_db()

    event = AuditEvent(
        actor_id="x" * 200,  # Will be clipped to 128
        actor_type="user",
        object_type="test_object",
        object_id="123",
        action="test_action",
        result="success",
    )

    audit_id = service.write_event(event, session=session)
    audit_log = session.query(AuditLog).filter_by(id=uuid.UUID(audit_id)).first()

    assert len(audit_log.actor_id) == 128
    session.close()
