from datetime import datetime, timezone
import uuid

import pytest

from db.models import BacktestRun, M2Report, ShadowRun
from services.launch_review import LaunchReviewService


UTC = timezone.utc


def _seed_backtest(session, *, recommendation: str = "go") -> BacktestRun:
    now = datetime.now(UTC)
    run = BacktestRun(
        id=uuid.uuid4(),
        run_name="bt-seed",
        status="completed",
        recommendation=recommendation,
        window_start=now,
        window_end=now,
        strategy_version="baseline-v1",
        executed_by="researcher",
        parameters={"window_days": 30},
        summary={"totals": {"candidate_count": 1}},
        completed_at=now,
    )
    session.add(run)
    session.commit()
    return run


def _seed_shadow(session, *, recommendation: str = "go", risk_state: str = "Normal") -> ShadowRun:
    now = datetime.now(UTC)
    run = ShadowRun(
        id=uuid.uuid4(),
        run_name="shadow-seed",
        risk_state=risk_state,
        recommendation=recommendation,
        executed_by="ops",
        summary={},
        checklist=[{"code": "risk_state_safe", "label": "safe", "passed": recommendation != "block"}],
        completed_at=now,
    )
    session.add(run)
    session.commit()
    return run


def _seed_stage_review(session, *, stage_name: str = "M6", decision: str = "Go") -> M2Report:
    now = datetime.now(UTC)
    report = M2Report(
        id=uuid.uuid4(),
        report_type=f"stage_review:{stage_name}",
        report_period_start=now,
        report_period_end=now,
        report_data={"stage_name": stage_name, "decision": decision},
        generated_at=now,
        generated_by="reporter",
    )
    session.add(report)
    session.commit()
    return report


def test_create_review_builds_default_checklist(test_db):
    session = test_db()
    backtest = _seed_backtest(session, recommendation="go")
    shadow = _seed_shadow(session, recommendation="go", risk_state="Normal")
    stage_review = _seed_stage_review(session, stage_name="M6", decision="Go")

    service = LaunchReviewService(session)
    review = service.create_review(
        title="Launch readiness",
        stage_name="M6",
        requested_by="ops_lead",
        shadow_run_id=shadow.id,
    )

    assert review.status == "pending"
    assert review.shadow_run_id == shadow.id
    assert review.evidence_summary["latest_backtest"]["id"] == str(backtest.id)
    assert review.evidence_summary["latest_stage_review"]["id"] == str(stage_review.id)
    assert any(item["code"] == "shadow_not_blocked" and item["passed"] is True for item in review.checklist)
    assert any(item["code"] == "latest_stage_review_go" and item["passed"] is True for item in review.checklist)
    session.close()


def test_decide_review_blocks_go_when_checklist_has_failures(test_db):
    session = test_db()
    _seed_backtest(session, recommendation="nogo")
    shadow = _seed_shadow(session, recommendation="block", risk_state="RiskOff")
    _seed_stage_review(session, stage_name="M6", decision="NoGo")

    service = LaunchReviewService(session)
    review = service.create_review(
        title="Launch readiness",
        stage_name="M6",
        requested_by="ops_lead",
        shadow_run_id=shadow.id,
    )

    with pytest.raises(ValueError):
        service.decide(review.id, decision="go", reviewed_by="reviewer_a", notes="force go")

    decided = service.decide(review.id, decision="nogo", reviewed_by="reviewer_a", notes="blocked")
    assert decided.status == "nogo"
    assert decided.reviewed_by == "reviewer_a"
    session.close()
