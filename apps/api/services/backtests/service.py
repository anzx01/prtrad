from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import BacktestRun, Market, NetEVCandidate, RiskStateEvent
from services.audit import AuditEvent
from services.risk.clustering import load_latest_classifications, resolve_cluster_code


_STRESS_HAIRCUTS = {
    "baseline": Decimal("1.0"),
    "haircut_20": Decimal("0.8"),
    "haircut_40": Decimal("0.6"),
}


class BacktestService:
    def __init__(self, db: Session, audit_service: Any | None = None) -> None:
        self.db = db
        if audit_service is None:
            from services.audit import get_audit_log_service

            audit_service = get_audit_log_service()
        self.audit_service = audit_service

    def list_runs(self, limit: int = 20) -> list[BacktestRun]:
        return list(
            self.db.scalars(
                select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)
            ).all()
        )

    def get_run(self, run_id: uuid.UUID) -> BacktestRun | None:
        return self.db.get(BacktestRun, run_id)

    def create_run(
        self,
        *,
        run_name: str,
        window_days: int = 30,
        executed_by: str | None = None,
        strategy_version: str | None = None,
        as_of: datetime | None = None,
    ) -> BacktestRun:
        run_end = as_of or datetime.now(UTC)
        run_start = run_end - timedelta(days=max(1, window_days))
        candidate_rows = self._load_latest_candidates(run_start=run_start, run_end=run_end)
        classifications = load_latest_classifications(
            self.db,
            [candidate.market_ref_id for candidate, _ in candidate_rows],
        )

        decision_breakdown = {"admit": 0, "reject": 0}
        cluster_breakdown: dict[str, int] = {}
        admitted_net_evs: list[Decimal] = []
        resolved_market_count = 0

        for candidate, market in candidate_rows:
            decision = str(candidate.admission_decision)
            if decision not in decision_breakdown:
                decision_breakdown[decision] = 0
            decision_breakdown[decision] += 1

            classification = classifications.get(candidate.market_ref_id)
            cluster_code = resolve_cluster_code(market=market, classification_result=classification)
            cluster_breakdown[cluster_code] = cluster_breakdown.get(cluster_code, 0) + 1

            if market.final_resolution:
                resolved_market_count += 1

            if candidate.admission_decision == "admit":
                admitted_net_evs.append(Decimal(str(candidate.net_ev)))

        total_candidates = len(candidate_rows)
        admitted_count = decision_breakdown.get("admit", 0)
        rejected_count = decision_breakdown.get("reject", 0)
        avg_net_ev = (
            float(sum(admitted_net_evs, Decimal("0")) / len(admitted_net_evs))
            if admitted_net_evs
            else 0.0
        )

        risk_events = list(
            self.db.scalars(
                select(RiskStateEvent)
                .where(RiskStateEvent.created_at >= run_start)
                .where(RiskStateEvent.created_at <= run_end)
                .order_by(RiskStateEvent.created_at.desc())
            ).all()
        )
        stress_tests = self._build_stress_tests(admitted_net_evs)
        recommendation = self._resolve_recommendation(
            total_candidates=total_candidates,
            admitted_count=admitted_count,
            stress_tests=stress_tests,
            risk_events=risk_events,
        )

        summary = {
            "totals": {
                "candidate_count": total_candidates,
                "admitted_count": admitted_count,
                "rejected_count": rejected_count,
                "resolved_market_count": resolved_market_count,
                "resolved_ratio": (resolved_market_count / total_candidates) if total_candidates else 0.0,
                "avg_admit_net_ev": avg_net_ev,
            },
            "cluster_breakdown": dict(
                sorted(cluster_breakdown.items(), key=lambda item: (-item[1], item[0]))
            ),
            "stress_tests": stress_tests,
            "risk_events": [
                {
                    "to_state": event.to_state,
                    "trigger_metric": event.trigger_metric,
                    "created_at": event.created_at.isoformat(),
                }
                for event in risk_events[:10]
            ],
            "benchmark": {
                "admit_rate": (admitted_count / total_candidates) if total_candidates else 0.0,
                "coverage_rate": (resolved_market_count / total_candidates) if total_candidates else 0.0,
            },
        }

        run = BacktestRun(
            id=uuid.uuid4(),
            run_name=run_name.strip() or f"backtest-{run_end:%Y%m%d%H%M%S}",
            status="completed",
            recommendation=recommendation,
            window_start=run_start,
            window_end=run_end,
            strategy_version=(strategy_version or "").strip() or None,
            executed_by=(executed_by or "").strip() or None,
            parameters={
                "window_days": window_days,
                "strategy_version": (strategy_version or "").strip() or None,
            },
            summary=summary,
            completed_at=run_end,
        )
        self.db.add(run)
        self.db.flush()
        self._write_audit(run=run)
        return run

    def serialize_run(self, run: BacktestRun) -> dict[str, Any]:
        return {
            "id": str(run.id),
            "run_name": run.run_name,
            "status": run.status,
            "recommendation": run.recommendation,
            "window_start": run.window_start.isoformat(),
            "window_end": run.window_end.isoformat(),
            "strategy_version": run.strategy_version,
            "executed_by": run.executed_by,
            "parameters": run.parameters,
            "summary": run.summary,
            "completed_at": run.completed_at.isoformat(),
            "created_at": run.created_at.isoformat(),
        }

    def _load_latest_candidates(
        self,
        *,
        run_start: datetime,
        run_end: datetime,
    ) -> list[tuple[NetEVCandidate, Market]]:
        candidate_rows = self.db.execute(
            select(NetEVCandidate, Market)
            .join(Market, NetEVCandidate.market_ref_id == Market.id)
            .where(NetEVCandidate.evaluated_at >= run_start)
            .where(NetEVCandidate.evaluated_at <= run_end)
            .order_by(
                NetEVCandidate.market_ref_id.asc(),
                NetEVCandidate.evaluated_at.desc(),
                NetEVCandidate.created_at.desc(),
            )
        ).all()

        latest_by_market: dict[uuid.UUID, tuple[NetEVCandidate, Market]] = {}
        for candidate, market in candidate_rows:
            latest_by_market.setdefault(candidate.market_ref_id, (candidate, market))
        return list(latest_by_market.values())

    def _build_stress_tests(self, admitted_net_evs: list[Decimal]) -> dict[str, dict[str, float | int]]:
        output: dict[str, dict[str, float | int]] = {}
        for scenario_name, multiplier in _STRESS_HAIRCUTS.items():
            adjusted = [net_ev * multiplier for net_ev in admitted_net_evs]
            positive_count = sum(1 for value in adjusted if value > 0)
            output[scenario_name] = {
                "positive_count": positive_count,
                "avg_net_ev": float(sum(adjusted, Decimal("0")) / len(adjusted)) if adjusted else 0.0,
            }
        return output

    def _resolve_recommendation(
        self,
        *,
        total_candidates: int,
        admitted_count: int,
        stress_tests: dict[str, dict[str, float | int]],
        risk_events: list[RiskStateEvent],
    ) -> str:
        if total_candidates == 0 or admitted_count == 0:
            return "nogo"
        if int(stress_tests["haircut_40"]["positive_count"]) == 0:
            return "watch"
        if any(event.to_state in {"RiskOff", "Frozen"} for event in risk_events):
            return "watch"
        return "go"

    def _write_audit(self, *, run: BacktestRun) -> None:
        if self.audit_service is None:
            return
        self.audit_service.safe_write_event(
            AuditEvent(
                actor_id=run.executed_by,
                actor_type="user" if run.executed_by else "system",
                object_type="backtest_run",
                object_id=str(run.id),
                action="execute",
                result=run.status,
                event_payload={
                    "run_name": run.run_name,
                    "recommendation": run.recommendation,
                    "window_start": run.window_start.isoformat(),
                    "window_end": run.window_end.isoformat(),
                },
            ),
            session=self.db,
        )
