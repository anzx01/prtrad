"""Integration tests for review queue compatibility."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import Market, MarketClassificationResult, MarketReviewTask
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_review_task(*, queue_status: str = "open") -> uuid.UUID:
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
                classification_status="classified",
                primary_category_code="Politics",
                admission_bucket_code="review",
                confidence=Decimal("0.62"),
                requires_review=True,
                conflict_count=1,
                failure_reason_code="LOW_CONFIDENCE",
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
                review_reason_code="LOW_CONFIDENCE",
                priority="high",
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
    assert "rejection_reason" in response.json()["detail"]
