import uuid
from unittest.mock import Mock

from services.scoring import ScoringService
from services.scoring.contracts import ScoringInput


def test_score_market_writes_audit_log_with_existing_session():
    db = Mock()
    audit_service = Mock()
    service = ScoringService(db, audit_service=audit_service, task_id="task-123")
    market_ref_id = uuid.uuid4()

    result = service.score_market(
        ScoringInput(
            market_ref_id=market_ref_id,
            question="Will ACME release 2026 Q2 revenue above $1 billion by July 31, 2026?",
            description="Resolve based on the official quarterly earnings release.",
            resolution_criteria="Use the company's official investor relations filing or earnings release.",
            primary_category_code="Numeric",
            admission_bucket_code="LIST_WHITE",
            classification_confidence=0.9,
        )
    )

    assert result.market_ref_id == market_ref_id
    audit_service.safe_write_event.assert_called_once()

    event = audit_service.safe_write_event.call_args.args[0]
    kwargs = audit_service.safe_write_event.call_args.kwargs
    assert event.object_type == "market_scoring"
    assert event.object_id == str(market_ref_id)
    assert event.task_id == "task-123"
    assert kwargs["session"] is db
