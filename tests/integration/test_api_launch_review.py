from datetime import datetime, timezone
import uuid

from db.models import BacktestRun, M2Report, ShadowRun
from tests.integration.conftest import TestSessionLocal


UTC = timezone.utc


def _seed_dependencies() -> str:
    session = TestSessionLocal()
    try:
        now = datetime.now(UTC)
        session.add(
            BacktestRun(
                id=uuid.uuid4(),
                run_name="api-bt",
                status="completed",
                recommendation="go",
                window_start=now,
                window_end=now,
                strategy_version="baseline-v1",
                executed_by="research",
                parameters={"window_days": 30},
                summary={"totals": {"candidate_count": 1}},
                completed_at=now,
            )
        )
        shadow_run = ShadowRun(
            id=uuid.uuid4(),
            run_name="api-shadow",
            risk_state="Normal",
            recommendation="go",
            executed_by="ops",
            summary={},
            checklist=[{"code": "risk_state_safe", "label": "safe", "passed": True}],
            completed_at=now,
        )
        session.add(shadow_run)
        session.add(
            M2Report(
                id=uuid.uuid4(),
                report_type="stage_review:M6",
                report_period_start=now,
                report_period_end=now,
                report_data={"stage_name": "M6", "decision": "Go"},
                generated_at=now,
                generated_by="reporter",
            )
        )
        session.commit()
        return str(shadow_run.id)
    finally:
        session.close()


def test_create_and_decide_launch_review(client):
    shadow_run_id = _seed_dependencies()

    create_response = client.post(
        "/launch-review",
        json={
            "title": "API Launch Review",
            "stage_name": "M6",
            "requested_by": "ops_api",
            "shadow_run_id": shadow_run_id,
        },
    )
    assert create_response.status_code == 200
    review = create_response.json()["review"]
    assert review["status"] == "pending"

    decide_response = client.post(
        f"/launch-review/{review['id']}/decide",
        json={"decision": "go", "reviewed_by": "lead_api", "notes": "ready"},
    )
    assert decide_response.status_code == 200
    decided = decide_response.json()["review"]
    assert decided["status"] == "go"

    list_response = client.get("/launch-review")
    assert list_response.status_code == 200
    assert len(list_response.json()["reviews"]) == 1
