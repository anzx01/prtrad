"""
Unit tests for audit log service.
"""
import uuid
import pytest
from unittest.mock import Mock

from db.models import AuditLog
from services.audit.service import AuditLogService
from services.audit.contracts import AuditEvent


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
