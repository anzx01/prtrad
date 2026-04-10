from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from sqlalchemy import select

from db.models import AuditLog, KillSwitchRequest, Market, NetEVCandidate, RiskStateEvent
from services.shadow import ShadowRunService


UTC = timezone.utc


def _seed_admitted_candidate(session, *, market_code: str, net_ev: str) -> None:
    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    session.add(
        Market(
            id=market_id,
            market_id=market_code,
            question=f"{market_code} question?",
            category_raw="Politics",
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=2),
            close_time=now + timedelta(days=2),
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
            admission_decision="admit",
            rejection_reason_code=None,
            evaluated_at=now,
        )
    )
    session.commit()


def test_execute_shadow_run_returns_go_when_system_is_clean(test_db):
    session = test_db()
    _seed_admitted_candidate(session, market_code="shadow-go", net_ev="0.150000")

    service = ShadowRunService(session)
    run = service.execute(run_name="shadow-go", executed_by="ops_a")

    assert run.recommendation == "go"
    assert run.summary["candidate_summary"]["admitted_market_count"] == 1
    audit_event = session.scalar(select(AuditLog).where(AuditLog.object_type == "shadow_run"))
    assert audit_event is not None
    session.close()


def test_execute_shadow_run_blocks_when_pending_kill_switch_exists(test_db):
    session = test_db()
    _seed_admitted_candidate(session, market_code="shadow-block", net_ev="0.150000")
    session.add(
        KillSwitchRequest(
            id=uuid.uuid4(),
            request_type="freeze",
            target_scope="global",
            requested_by="ops",
            reason="manual hold",
            status="pending",
        )
    )
    session.add(
        RiskStateEvent(
            id=uuid.uuid4(),
            from_state="Normal",
            to_state="Caution",
            trigger_type="auto",
            trigger_metric="global.utilization_rate",
            trigger_value=Decimal("0.610000"),
            threshold_value=Decimal("0.600000"),
            actor_id=None,
            notes="seed",
        )
    )
    session.commit()

    service = ShadowRunService(session)
    run = service.execute(run_name="shadow-block", executed_by="ops_b")

    assert run.recommendation == "watch"
    assert any(item["code"] == "kill_switch_queue_clear" and item["passed"] is False for item in run.checklist)
    session.close()
