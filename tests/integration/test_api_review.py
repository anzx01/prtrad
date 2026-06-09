"""Integration tests for review queue compatibility."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, MarketClassificationResult, MarketReviewTask
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_review_task(
    *,
    queue_status: str = "open",
    primary_category_code: str | None = "Politics",
    classification_status: str = "classified",
    admission_bucket_code: str = "review",
    requires_review: bool = True,
    conflict_count: int = 1,
    review_reason_code: str = "LOW_CONFIDENCE",
    priority: str = "high",
    failure_reason_code: str = "LOW_CONFIDENCE",
) -> uuid.UUID:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        market_id = uuid.uuid4()
        classification_id = uuid.uuid4()
        review_task_id = uuid.uuid4()

        session.add(
            Market(
                id=market_id,
                market_id=f"review-market-{review_task_id.hex[:8]}",
                question="Will the review queue show this market?",
                category_raw="Politics",
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=2),
                open_time=now - timedelta(days=1),
                close_time=now + timedelta(days=1),
                source_updated_at=now,
            )
        )
        session.add(
            MarketClassificationResult(
                id=classification_id,
                market_ref_id=market_id,
                rule_version="rules_v1",
                source_fingerprint=f"fp-{review_task_id.hex}",
                classification_status=classification_status,
                primary_category_code=primary_category_code,
                admission_bucket_code=admission_bucket_code,
                confidence=Decimal("0.62"),
                requires_review=requires_review,
                conflict_count=conflict_count,
                failure_reason_code=failure_reason_code,
                result_details={"source": "integration-test"},
                classified_at=now,
            )
        )
        session.add(
            MarketReviewTask(
                id=review_task_id,
                market_ref_id=market_id,
                classification_result_id=classification_id,
                queue_status=queue_status,
                review_reason_code=review_reason_code,
                priority=priority,
                review_payload={"source": "integration-test"},
            )
        )
        session.commit()
        return review_task_id
    finally:
        session.close()


def test_review_queue_pending_includes_legacy_open_tasks(client):
    task_id = _seed_review_task(queue_status="open")

    response = client.get("/review/queue?queue_status=pending")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["id"] == str(task_id)
    assert data["tasks"][0]["queue_status"] == "pending"
    assert data["tasks"][0]["can_approve"] is True
    assert data["tasks"][0]["approval_block_reason"] is None
    assert data["tasks"][0]["system_next_action"] == "approve"
    assert data["tasks"][0]["system_conclusion_code"] == "APPROVE_READY"
    assert data["tasks"][0]["classification_result"]["primary_category_code"] == "Politics"

    detail_response = client.get(f"/review/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["task"]["queue_status"] == "pending"


def test_legacy_open_review_task_can_start_review(client):
    task_id = _seed_review_task(queue_status="open")

    response = client.patch(
        f"/review/{task_id}",
        json={"queue_status": "in_progress", "assigned_to": "reviewer_1"},
    )
    assert response.status_code == 200

    task = response.json()["task"]
    assert task["queue_status"] == "in_progress"
    assert task["assigned_to"] == "reviewer_1"


def test_monitoring_counts_legacy_open_tasks_as_pending(client):
    _seed_review_task(queue_status="open")

    response = client.get("/monitoring/metrics")
    assert response.status_code == 200

    metrics = response.json()["metrics"]["review_queue"]
    assert metrics["pending"] == 1


def test_review_queue_total_counts_all_matching_tasks(client):
    _seed_review_task(queue_status="open")
    _seed_review_task(queue_status="pending")

    response = client.get("/review/queue?queue_status=pending&page=1&page_size=1")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["tasks"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 1


def test_bulk_review_action_can_start_pending_tasks(client):
    task_id = _seed_review_task(queue_status="pending")

    response = client.post(
        "/review/bulk-action",
        json={
            "task_ids": [str(task_id)],
            "action": "start_review",
            "actor_id": "reviewer_bulk",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["updated_count"] == 1
    assert data["tasks"][0]["queue_status"] == "in_progress"
    assert data["tasks"][0]["assigned_to"] == "reviewer_bulk"


def test_bulk_review_action_can_approve_pending_tasks_directly(client):
    first_task_id = _seed_review_task(queue_status="pending")
    second_task_id = _seed_review_task(queue_status="open")

    response = client.post(
        "/review/bulk-action",
        json={
            "task_ids": [str(first_task_id), str(second_task_id)],
            "action": "approve",
            "actor_id": "reviewer_bulk",
            "notes": "bulk approve",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["updated_count"] == 2
    assert [task["queue_status"] for task in data["tasks"]] == ["approved", "approved"]

    detail_first = client.get(f"/review/{first_task_id}")
    detail_second = client.get(f"/review/{second_task_id}")
    assert detail_first.status_code == 200
    assert detail_second.status_code == 200
    assert detail_first.json()["task"]["queue_status"] == "approved"
    assert detail_second.json()["task"]["queue_status"] == "approved"


def test_bulk_review_reject_requires_reason(client):
    task_id = _seed_review_task(queue_status="pending")

    response = client.post(
        "/review/bulk-action",
        json={
            "task_ids": [str(task_id)],
            "action": "reject",
            "actor_id": "reviewer_bulk",
        },
    )
    assert response.status_code == 400
    assert "退回原因" in response.json()["detail"]


def test_review_task_without_formal_primary_category_can_reject_without_manual_reason(client):
    task_id = _seed_review_task(
        queue_status="pending",
        primary_category_code=None,
        classification_status="ReviewRequired",
        requires_review=True,
        conflict_count=0,
        review_reason_code="TAG_NO_CATEGORY_MATCH",
        priority="normal",
        failure_reason_code="TAG_NO_CATEGORY_MATCH",
    )

    response = client.post(
        f"/review/{task_id}/reject",
        json={
            "actor_id": "reviewer_blocked",
        },
    )
    assert response.status_code == 200

    task = response.json()["task"]
    assert task["queue_status"] == "rejected"
    assert task["auto_reject_reason_code"] == "TAG_NO_CATEGORY_MATCH"

    detail_response = client.get(f"/review/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["task"]["review_payload"]["rejection_reason"] == "TAG_NO_CATEGORY_MATCH"
    assert detail_response.json()["task"]["review_payload"]["rejection_reason_auto_filled"] is True


def test_bulk_reject_can_use_system_reason_for_unapprovable_tasks(client):
    first_task_id = _seed_review_task(
        queue_status="pending",
        primary_category_code=None,
        classification_status="ReviewRequired",
        requires_review=True,
        conflict_count=0,
        review_reason_code="TAG_NO_CATEGORY_MATCH",
        priority="normal",
        failure_reason_code="TAG_NO_CATEGORY_MATCH",
    )
    second_task_id = _seed_review_task(
        queue_status="pending",
        primary_category_code="CAT_SPORTS",
        classification_status="Blocked",
        admission_bucket_code="LIST_BLACK",
        requires_review=False,
        conflict_count=0,
        review_reason_code="TAG_BLACKLIST_MATCH",
        priority="high",
        failure_reason_code="TAG_BLACKLIST_MATCH",
    )

    response = client.post(
        "/review/bulk-action",
        json={
            "task_ids": [str(first_task_id), str(second_task_id)],
            "action": "reject",
            "actor_id": "reviewer_bulk",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["updated_count"] == 2
    assert [task["queue_status"] for task in data["tasks"]] == ["rejected", "rejected"]

    first_detail = client.get(f"/review/{first_task_id}")
    second_detail = client.get(f"/review/{second_task_id}")
    assert first_detail.status_code == 200
    assert second_detail.status_code == 200
    assert first_detail.json()["task"]["review_payload"]["rejection_reason"] == "TAG_NO_CATEGORY_MATCH"
    assert second_detail.json()["task"]["review_payload"]["rejection_reason"] == "TAG_BLACKLIST_MATCH"


def test_review_task_without_formal_primary_category_cannot_be_approved(client):
    task_id = _seed_review_task(
        queue_status="pending",
        primary_category_code=None,
        classification_status="ReviewRequired",
        requires_review=True,
        conflict_count=0,
        review_reason_code="TAG_NO_CATEGORY_MATCH",
        priority="normal",
        failure_reason_code="TAG_NO_CATEGORY_MATCH",
    )

    response = client.post(
        f"/review/{task_id}/approve",
        json={
            "actor_id": "reviewer_blocked",
            "approval_notes": "should be rejected",
        },
    )
    assert response.status_code == 400
    assert "缺少正式主类别" in response.json()["detail"]

    detail_response = client.get(f"/review/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["task"]["queue_status"] == "pending"


def test_bulk_approve_returns_clear_error_when_selection_contains_unapprovable_task(client):
    approvable_task_id = _seed_review_task(queue_status="pending")
    blocked_task_id = _seed_review_task(
        queue_status="pending",
        primary_category_code=None,
        classification_status="ReviewRequired",
        requires_review=True,
        conflict_count=0,
        review_reason_code="TAG_NO_CATEGORY_MATCH",
        priority="normal",
        failure_reason_code="TAG_NO_CATEGORY_MATCH",
    )

    queue_response = client.get("/review/queue?queue_status=pending&page=1&page_size=20")
    assert queue_response.status_code == 200
    queue_tasks = {task["id"]: task for task in queue_response.json()["tasks"]}
    assert queue_tasks[str(approvable_task_id)]["can_approve"] is True
    assert queue_tasks[str(blocked_task_id)]["can_approve"] is False
    assert "正式主类别" in queue_tasks[str(blocked_task_id)]["approval_block_reason"]
    assert queue_tasks[str(blocked_task_id)]["system_next_action"] == "reject"
    assert queue_tasks[str(blocked_task_id)]["auto_reject_reason_code"] == "TAG_NO_CATEGORY_MATCH"

    response = client.post(
        "/review/bulk-action",
        json={
            "task_ids": [str(approvable_task_id), str(blocked_task_id)],
            "action": "approve",
            "actor_id": "reviewer_bulk",
            "notes": "should fail",
        },
    )
    assert response.status_code == 400
    assert "当前不允许批准" in response.json()["detail"]

    approvable_detail = client.get(f"/review/{approvable_task_id}")
    blocked_detail = client.get(f"/review/{blocked_task_id}")
    assert approvable_detail.status_code == 200
    assert blocked_detail.status_code == 200
    assert approvable_detail.json()["task"]["queue_status"] == "pending"
    assert blocked_detail.json()["task"]["queue_status"] == "pending"


def test_blocked_review_task_cannot_be_approved(client):
    task_id = _seed_review_task(
        queue_status="pending",
        primary_category_code="CAT_SPORTS",
        classification_status="Blocked",
        admission_bucket_code="LIST_BLACK",
        requires_review=False,
        conflict_count=0,
        review_reason_code="TAG_BLACKLIST_MATCH",
        priority="high",
        failure_reason_code="TAG_BLACKLIST_MATCH",
    )

    queue_response = client.get("/review/queue?queue_status=pending&page=1&page_size=20")
    assert queue_response.status_code == 200
    queue_tasks = {task["id"]: task for task in queue_response.json()["tasks"]}
    assert queue_tasks[str(task_id)]["can_approve"] is False
    assert "命中阻断规则" in queue_tasks[str(task_id)]["approval_block_reason"]
    assert queue_tasks[str(task_id)]["system_conclusion_code"] == "AUTO_BLOCKED"
    assert queue_tasks[str(task_id)]["auto_reject_reason_code"] == "TAG_BLACKLIST_MATCH"

    response = client.post(
        f"/review/{task_id}/approve",
        json={
            "actor_id": "reviewer_blocked",
            "approval_notes": "should not pass",
        },
    )
    assert response.status_code == 400
    assert "命中阻断规则" in response.json()["detail"]
