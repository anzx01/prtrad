from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import KillSwitchRequest, ShadowRun
from services.audit import AuditEvent
from services.monitoring import MonitoringService
from services.risk.clustering import load_latest_admitted_candidates
from services.risk.service import RiskService


class ShadowRunService:
    def __init__(self, db: Session, audit_service: Any | None = None) -> None:
        self.db = db
        if audit_service is None:
            from services.audit import get_audit_log_service

            audit_service = get_audit_log_service()
        self.audit_service = audit_service

    def list_runs(self, limit: int = 20) -> list[ShadowRun]:
        return list(
            self.db.scalars(select(ShadowRun).order_by(ShadowRun.created_at.desc()).limit(limit)).all()
        )

    def get_run(self, run_id: uuid.UUID) -> ShadowRun | None:
        return self.db.get(ShadowRun, run_id)

    def execute(self, *, run_name: str, executed_by: str | None = None) -> ShadowRun:
        now = datetime.now(UTC)
        risk_service = RiskService(self.db)
        monitoring_service = MonitoringService(self.db)

        risk_state = risk_service.get_current_state()
        exposures = risk_service.list_exposures()
        breached_clusters = [
            exposure.cluster_code
            for exposure in exposures
            if exposure.is_breached or Decimal(str(exposure.utilization_rate)) >= Decimal("1")
        ]

        monitoring_metrics = monitoring_service.get_metrics()["metrics"]
        pending_kill_switch = self.db.scalar(
            select(func.count(KillSwitchRequest.id)).where(KillSwitchRequest.status == "pending")
        )
        latest_candidates = load_latest_admitted_candidates(self.db)
        top_candidates = sorted(
            latest_candidates,
            key=lambda row: Decimal(str(row[0].net_ev)),
            reverse=True,
        )[:5]

        checklist = [
            {
                "code": "risk_state_safe",
                "label": "Risk state is not RiskOff/Frozen",
                "passed": risk_state not in {"RiskOff", "Frozen"},
            },
            {
                "code": "cluster_limits_clean",
                "label": "No breached exposure clusters",
                "passed": len(breached_clusters) == 0,
            },
            {
                "code": "dq_alerts_clean",
                "label": "No recent DQ failures in monitoring",
                "passed": int(monitoring_metrics["dq"]["recent_failures"]) == 0,
            },
            {
                "code": "kill_switch_queue_clear",
                "label": "No pending kill-switch requests",
                "passed": int(pending_kill_switch or 0) == 0,
            },
        ]

        recommendation = self._resolve_recommendation(
            risk_state=risk_state,
            breached_clusters=breached_clusters,
            pending_kill_switch=int(pending_kill_switch or 0),
            recent_failures=int(monitoring_metrics["dq"]["recent_failures"]),
        )

        summary = {
            "risk_state": risk_state,
            "exposure_summary": {
                "cluster_count": len(exposures),
                "breached_clusters": breached_clusters,
            },
            "monitoring": monitoring_metrics,
            "candidate_summary": {
                "admitted_market_count": len(latest_candidates),
                "top_candidates": [
                    {
                        "market_id": market.market_id,
                        "question": market.question,
                        "net_ev": float(candidate.net_ev),
                    }
                    for candidate, market in top_candidates
                ],
            },
            "decision_rationale": [
                item["label"]
                for item in checklist
                if not bool(item["passed"])
            ],
        }

        run = ShadowRun(
            id=uuid.uuid4(),
            run_name=run_name.strip() or f"shadow-{now:%Y%m%d%H%M%S}",
            risk_state=risk_state,
            recommendation=recommendation,
            executed_by=(executed_by or "").strip() or None,
            summary=summary,
            checklist=checklist,
            completed_at=now,
        )
        self.db.add(run)
        self.db.flush()
        self._write_audit(run=run)
        return run

    def serialize_run(self, run: ShadowRun) -> dict[str, Any]:
        return {
            "id": str(run.id),
            "run_name": run.run_name,
            "risk_state": run.risk_state,
            "recommendation": run.recommendation,
            "executed_by": run.executed_by,
            "summary": run.summary,
            "checklist": run.checklist,
            "completed_at": run.completed_at.isoformat(),
            "created_at": run.created_at.isoformat(),
        }

    def _resolve_recommendation(
        self,
        *,
        risk_state: str,
        breached_clusters: list[str],
        pending_kill_switch: int,
        recent_failures: int,
    ) -> str:
        if risk_state in {"RiskOff", "Frozen"} or breached_clusters or recent_failures > 0:
            return "block"
        if risk_state == "Caution" or pending_kill_switch > 0:
            return "watch"
        return "go"

    def _write_audit(self, *, run: ShadowRun) -> None:
        if self.audit_service is None:
            return
        self.audit_service.safe_write_event(
            AuditEvent(
                actor_id=run.executed_by,
                actor_type="user" if run.executed_by else "system",
                object_type="shadow_run",
                object_id=str(run.id),
                action="execute",
                result=run.recommendation,
                event_payload={
                    "run_name": run.run_name,
                    "risk_state": run.risk_state,
                },
            ),
            session=self.db,
        )
