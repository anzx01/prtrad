from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from db.models import AuditLog, BacktestRun, Market, NetEVCandidate, RiskStateEvent, ShadowRun
from services.reports import ReportService


UTC = timezone.utc


def _seed_daily_inputs(session) -> None:
    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    session.add(
        Market(
            id=market_id,
            market_id="report-market",
            question="report-market question?",
            category_raw="Politics",
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=1),
            open_time=now - timedelta(days=1),
            close_time=now + timedelta(days=1),
            source_updated_at=now,
        )
    )
    session.add(
        NetEVCandidate(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            calibration_unit_id=None,
            gross_edge=Decimal("0.100000"),
            fee_cost=Decimal("0.010000"),
            slippage_cost=Decimal("0.005000"),
            dispute_discount=Decimal("0.002000"),
            net_ev=Decimal("0.100000"),
            admission_decision="admit",
            rejection_reason_code=None,
            evaluated_at=now - timedelta(hours=1),
        )
    )
    session.add(
        RiskStateEvent(
            id=uuid.uuid4(),
            from_state="Normal",
            to_state="Caution",
            trigger_type="auto",
            trigger_metric="global.utilization_rate",
            trigger_value=Decimal("0.700000"),
            threshold_value=Decimal("0.600000"),
            actor_id=None,
            notes="seed",
        )
    )
    session.add(
        AuditLog(
            id=uuid.uuid4(),
            actor_id="system",
            actor_type="service",
            object_type="risk_state",
            object_id="seed-risk-state",
            action="auto_transition",
            result="success",
            event_payload={"seed": True},
        )
    )
    session.commit()


def test_generate_daily_summary_report(test_db):
    session = test_db()
    _seed_daily_inputs(session)

    service = ReportService(session)
    report = service.generate_report(report_type="daily_summary", generated_by="tester")

    assert report.report_type == "daily_summary"
    assert report.report_data["summary"]["candidate_total"] == 1
    assert report.report_data["summary"]["auditable"] is True
    assert service.list_reports()[0]["id"] == str(report.id)
    session.close()


def test_generate_stage_review_uses_latest_backtest_and_shadow(test_db):
    session = test_db()
    now = datetime.now(UTC)
    session.add(
        BacktestRun(
            id=uuid.uuid4(),
            run_name="stage-bt",
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
    session.add(
        ShadowRun(
            id=uuid.uuid4(),
            run_name="stage-shadow",
            risk_state="Normal",
            recommendation="go",
            executed_by="ops",
            summary={},
            checklist=[],
            completed_at=now,
        )
    )
    session.add(
        AuditLog(
            id=uuid.uuid4(),
            actor_id="system",
            actor_type="service",
            object_type="shadow_run",
            object_id="seed-shadow",
            action="execute",
            result="go",
            event_payload={"seed": True},
        )
    )
    session.commit()

    service = ReportService(session)
    report = service.generate_report(report_type="stage_review", generated_by="tester", stage_name="M6")

    assert report.report_data["decision"] == "Go"
    assert report.report_data["dod"]["backtest_available"] is True
    assert report.report_data["latest_shadow_run"]["run_name"] == "stage-shadow"
    session.close()
