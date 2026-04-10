from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from sqlalchemy import select

from db.models import AuditLog, Market, NetEVCandidate, RiskStateEvent
from services.backtests import BacktestService


UTC = timezone.utc


def _seed_candidate(
    session,
    *,
    market_code: str,
    net_ev: str,
    decision: str = "admit",
    final_resolution: str | None = None,
) -> None:
    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    session.add(
        Market(
            id=market_id,
            market_id=market_code,
            question=f"{market_code} question?",
            category_raw="Politics",
            final_resolution=final_resolution,
            market_status="resolved" if final_resolution else "active_accepting_orders",
            creation_time=now - timedelta(days=3),
            open_time=now - timedelta(days=3),
            close_time=now + timedelta(days=3),
            resolution_time=now - timedelta(hours=12) if final_resolution else None,
            source_updated_at=now,
        )
    )
    session.add(
        NetEVCandidate(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            calibration_unit_id=None,
            gross_edge=Decimal(net_ev),
            fee_cost=Decimal("0.010000"),
            slippage_cost=Decimal("0.005000"),
            dispute_discount=Decimal("0.002000"),
            net_ev=Decimal(net_ev),
            admission_decision=decision,
            rejection_reason_code=None if decision == "admit" else "REJ_COST_NEG_NETEV",
            evaluated_at=now - timedelta(hours=1),
        )
    )
    session.commit()


def test_create_run_builds_summary_and_stress_tests(test_db):
    session = test_db()
    _seed_candidate(session, market_code="bt-1", net_ev="0.200000", final_resolution="yes")
    _seed_candidate(session, market_code="bt-2", net_ev="0.120000")
    _seed_candidate(session, market_code="bt-3", net_ev="-0.010000", decision="reject")

    service = BacktestService(session)
    run = service.create_run(run_name="m5-baseline", window_days=30, executed_by="research_a")

    assert run.recommendation in {"go", "watch"}
    assert run.summary["totals"]["candidate_count"] == 3
    assert run.summary["totals"]["admitted_count"] == 2
    assert run.summary["totals"]["rejected_count"] == 1
    assert run.summary["totals"]["resolved_market_count"] == 1
    assert "haircut_40" in run.summary["stress_tests"]
    assert run.summary["stress_tests"]["haircut_20"]["positive_count"] == 2
    session.close()


def test_create_run_writes_audit_log(test_db):
    session = test_db()
    _seed_candidate(session, market_code="bt-audit", net_ev="0.080000")
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
    session.commit()

    service = BacktestService(session)
    run = service.create_run(run_name="m5-audit", window_days=30, executed_by="research_a")

    audit_events = list(
        session.scalars(
            select(AuditLog).where(AuditLog.object_type == "backtest_run").order_by(AuditLog.created_at.desc())
        ).all()
    )
    assert audit_events
    assert audit_events[0].object_id == str(run.id)
    assert audit_events[0].action == "execute"
    session.close()
