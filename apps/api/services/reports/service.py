from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import AuditLog, BacktestRun, M2Report, NetEVCandidate, RiskExposure, RiskStateEvent, ShadowRun
from services.monitoring import MonitoringService


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def list_reports(self, report_type: str | None = None) -> list[dict[str, Any]]:
        statement = select(M2Report).order_by(M2Report.generated_at.desc())
        if report_type:
            statement = statement.where(M2Report.report_type == report_type)

        reports = self.db.scalars(statement).all()
        return [self.serialize_report(report) for report in reports]

    def generate_report(
        self,
        *,
        report_type: str,
        generated_by: str | None = None,
        days: int | None = None,
        stage_name: str | None = None,
    ) -> M2Report:
        now = datetime.now(UTC)
        normalized_type = report_type.strip().lower()
        period_days = days if days is not None else (1 if normalized_type == "daily_summary" else 7)
        period_end = now
        period_start = now - timedelta(days=max(1, period_days))

        persisted_type = normalized_type
        if normalized_type == "stage_review" and stage_name:
            persisted_type = f"stage_review:{stage_name.strip() or 'M6'}"

        existing = self.db.scalar(
            select(M2Report).where(
                M2Report.report_type == persisted_type,
                M2Report.report_period_start == period_start,
                M2Report.report_period_end == period_end,
            )
        )
        if existing is not None:
            return existing

        report_data = self._build_report_data(
            report_type=normalized_type,
            period_start=period_start,
            period_end=period_end,
            stage_name=stage_name,
        )

        report = M2Report(
            id=uuid.uuid4(),
            report_type=persisted_type,
            report_period_start=period_start,
            report_period_end=period_end,
            report_data=report_data,
            generated_at=now,
            generated_by=(generated_by or "").strip() or None,
        )
        self.db.add(report)
        self.db.flush()
        return report

    def list_audit_events(self, limit: int = 50) -> list[dict[str, Any]]:
        events = self.db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
        return [
            {
                "id": str(event.id),
                "actor_id": event.actor_id,
                "actor_type": event.actor_type,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "action": event.action,
                "result": event.result,
                "event_payload": event.event_payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]

    def serialize_report(self, report: M2Report) -> dict[str, Any]:
        return {
            "id": str(report.id),
            "report_type": report.report_type,
            "report_period_start": report.report_period_start.isoformat(),
            "report_period_end": report.report_period_end.isoformat(),
            "generated_at": report.generated_at.isoformat(),
            "generated_by": report.generated_by,
            "report_data": report.report_data,
        }

    def _build_report_data(
        self,
        *,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
        stage_name: str | None,
    ) -> dict[str, Any]:
        if report_type == "daily_summary":
            return self._build_daily_summary(period_start=period_start, period_end=period_end)
        if report_type == "weekly_summary":
            return self._build_weekly_summary(period_start=period_start, period_end=period_end)
        if report_type == "stage_review":
            return self._build_stage_review(stage_name=stage_name, period_start=period_start, period_end=period_end)
        raise ValueError("report_type must be one of daily_summary, weekly_summary, stage_review")

    def _build_daily_summary(self, *, period_start: datetime, period_end: datetime) -> dict[str, Any]:
        candidates = list(
            self.db.scalars(
                select(NetEVCandidate)
                .where(NetEVCandidate.evaluated_at >= period_start)
                .where(NetEVCandidate.evaluated_at <= period_end)
                .order_by(NetEVCandidate.evaluated_at.desc())
            ).all()
        )
        decision_counts = {"admit": 0, "reject": 0}
        rejection_reason_counts: dict[str, int] = {}
        for candidate in candidates:
            decision = str(candidate.admission_decision)
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
            if candidate.rejection_reason_code:
                rejection_reason_counts[candidate.rejection_reason_code] = (
                    rejection_reason_counts.get(candidate.rejection_reason_code, 0) + 1
                )

        risk_events = list(
            self.db.scalars(
                select(RiskStateEvent)
                .where(RiskStateEvent.created_at >= period_start)
                .where(RiskStateEvent.created_at <= period_end)
                .order_by(RiskStateEvent.created_at.desc())
            ).all()
        )
        latest_exposures = self._latest_exposures()
        monitoring_metrics = MonitoringService(self.db).get_metrics()["metrics"]
        audit_count = self.db.scalar(
            select(func.count(AuditLog.id))
            .where(AuditLog.created_at >= period_start)
            .where(AuditLog.created_at <= period_end)
        ) or 0

        return {
            "summary": {
                "candidate_total": len(candidates),
                "admitted_count": decision_counts.get("admit", 0),
                "rejected_count": decision_counts.get("reject", 0),
                "audit_event_count": int(audit_count),
                "auditable": int(audit_count) > 0,
            },
            "rejection_reason_distribution": rejection_reason_counts,
            "risk_state_events": [
                {
                    "to_state": event.to_state,
                    "trigger_metric": event.trigger_metric,
                    "created_at": event.created_at.isoformat(),
                }
                for event in risk_events[:10]
            ],
            "current_exposures": latest_exposures,
            "dq_alert_snapshot": monitoring_metrics["dq"],
            "missing_sections": [] if int(audit_count) > 0 else ["audit_log"],
        }

    def _build_weekly_summary(self, *, period_start: datetime, period_end: datetime) -> dict[str, Any]:
        backtests = list(
            self.db.scalars(
                select(BacktestRun)
                .where(BacktestRun.created_at >= period_start)
                .where(BacktestRun.created_at <= period_end)
                .order_by(BacktestRun.created_at.desc())
            ).all()
        )
        risk_events = list(
            self.db.scalars(
                select(RiskStateEvent)
                .where(RiskStateEvent.created_at >= period_start)
                .where(RiskStateEvent.created_at <= period_end)
                .order_by(RiskStateEvent.created_at.desc())
            ).all()
        )
        recommendations = {"go": 0, "watch": 0, "nogo": 0}
        for run in backtests:
            recommendations[run.recommendation] = recommendations.get(run.recommendation, 0) + 1

        return {
            "summary": {
                "backtest_run_count": len(backtests),
                "risk_event_count": len(risk_events),
                "recommendation_breakdown": recommendations,
            },
            "recent_backtests": [
                {
                    "run_name": run.run_name,
                    "recommendation": run.recommendation,
                    "completed_at": run.completed_at.isoformat(),
                }
                for run in backtests[:10]
            ],
            "risk_timeline": [
                {
                    "to_state": event.to_state,
                    "created_at": event.created_at.isoformat(),
                }
                for event in risk_events[:10]
            ],
        }

    def _build_stage_review(
        self,
        *,
        stage_name: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        latest_backtest = self.db.scalar(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1))
        latest_shadow = self.db.scalar(select(ShadowRun).order_by(ShadowRun.created_at.desc()).limit(1))
        audit_count = self.db.scalar(
            select(func.count(AuditLog.id))
            .where(AuditLog.created_at >= period_start)
            .where(AuditLog.created_at <= period_end)
        ) or 0

        dod = {
            "state_alerts_available": True,
            "backtest_available": latest_backtest is not None,
            "shadow_run_available": latest_shadow is not None,
            "audit_available": int(audit_count) > 0,
        }
        nogo_reasons: list[str] = []
        if latest_backtest is None or latest_backtest.recommendation == "nogo":
            nogo_reasons.append("latest_backtest_not_ready")
        if latest_shadow is None or latest_shadow.recommendation == "block":
            nogo_reasons.append("latest_shadow_run_blocked")
        if int(audit_count) == 0:
            nogo_reasons.append("audit_log_missing")

        return {
            "stage_name": stage_name or "M6",
            "dod": dod,
            "decision": "NoGo" if nogo_reasons else "Go",
            "nogo_reasons": nogo_reasons,
            "latest_backtest": self._serialize_linked_run(latest_backtest),
            "latest_shadow_run": self._serialize_linked_run(latest_shadow),
        }

    def _serialize_linked_run(self, run: BacktestRun | ShadowRun | None) -> dict[str, Any] | None:
        if run is None:
            return None
        data = {
            "id": str(run.id),
            "run_name": run.run_name,
            "created_at": run.created_at.isoformat(),
        }
        if isinstance(run, BacktestRun):
            data["recommendation"] = run.recommendation
            data["window_end"] = run.window_end.isoformat()
        if isinstance(run, ShadowRun):
            data["recommendation"] = run.recommendation
            data["risk_state"] = run.risk_state
        return data

    def _latest_exposures(self) -> list[dict[str, Any]]:
        subquery = (
            select(
                RiskExposure.cluster_code,
                func.max(RiskExposure.snapshot_at).label("latest"),
            )
            .group_by(RiskExposure.cluster_code)
            .subquery()
        )
        exposures = self.db.scalars(
            select(RiskExposure).join(
                subquery,
                (RiskExposure.cluster_code == subquery.c.cluster_code)
                & (RiskExposure.snapshot_at == subquery.c.latest),
            )
        ).all()
        return [
            {
                "cluster_code": exposure.cluster_code,
                "utilization_rate": float(exposure.utilization_rate),
                "is_breached": exposure.is_breached,
            }
            for exposure in exposures
        ]
