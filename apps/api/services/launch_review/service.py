from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import BacktestRun, KillSwitchRequest, LaunchReview, ShadowRun
from services.audit import AuditEvent


class LaunchReviewService:
    def __init__(self, db: Session, audit_service: Any | None = None) -> None:
        self.db = db
        if audit_service is None:
            from services.audit import get_audit_log_service

            audit_service = get_audit_log_service()
        self.audit_service = audit_service

    def list_reviews(self, limit: int = 20) -> list[LaunchReview]:
        return list(
            self.db.scalars(
                select(LaunchReview).order_by(LaunchReview.created_at.desc()).limit(limit)
            ).all()
        )

    def get_review(self, review_id: uuid.UUID) -> LaunchReview | None:
        return self.db.get(LaunchReview, review_id)

    def create_review(
        self,
        *,
        title: str,
        stage_name: str,
        requested_by: str,
        shadow_run_id: uuid.UUID | None = None,
        checklist: list[dict[str, Any]] | None = None,
    ) -> LaunchReview:
        shadow_run = self.db.get(ShadowRun, shadow_run_id) if shadow_run_id else self._latest_shadow_run()
        latest_backtest = self._latest_backtest_run()
        review = LaunchReview(
            id=uuid.uuid4(),
            title=title.strip() or f"{stage_name.strip() or 'M6'} launch review",
            stage_name=stage_name.strip() or "M6",
            shadow_run_id=shadow_run.id if shadow_run else None,
            requested_by=requested_by.strip(),
            status="pending",
            checklist=checklist or self._build_default_checklist(shadow_run=shadow_run, backtest_run=latest_backtest),
            evidence_summary=self._build_evidence_summary(shadow_run=shadow_run, backtest_run=latest_backtest),
            review_notes=None,
            decided_at=None,
        )
        self.db.add(review)
        self.db.flush()
        self._write_audit(review=review, action="create", result="pending")
        return review

    def decide(
        self,
        review_id: uuid.UUID,
        *,
        decision: str,
        reviewed_by: str,
        notes: str | None = None,
    ) -> LaunchReview:
        review = self._require_review(review_id)
        normalized = decision.strip().lower()
        if normalized not in {"go", "nogo"}:
            raise ValueError("decision must be 'go' or 'nogo'")
        if normalized == "go" and self._has_failed_checklist(review.checklist):
            raise ValueError("cannot mark go when checklist contains failed items")

        review.status = normalized
        review.reviewed_by = reviewed_by.strip()
        review.review_notes = (notes or "").strip() or None
        review.decided_at = datetime.now(UTC)
        self.db.flush()
        self._write_audit(review=review, action="decide", result=normalized)
        return review

    def serialize_review(self, review: LaunchReview) -> dict[str, Any]:
        return {
            "id": str(review.id),
            "title": review.title,
            "stage_name": review.stage_name,
            "shadow_run_id": str(review.shadow_run_id) if review.shadow_run_id else None,
            "requested_by": review.requested_by,
            "reviewed_by": review.reviewed_by,
            "status": review.status,
            "checklist": review.checklist,
            "evidence_summary": review.evidence_summary,
            "review_notes": review.review_notes,
            "decided_at": review.decided_at.isoformat() if review.decided_at else None,
            "created_at": review.created_at.isoformat(),
        }

    def _latest_shadow_run(self) -> ShadowRun | None:
        return self.db.scalar(select(ShadowRun).order_by(ShadowRun.created_at.desc()).limit(1))

    def _latest_backtest_run(self) -> BacktestRun | None:
        return self.db.scalar(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1))

    def _build_default_checklist(
        self,
        *,
        shadow_run: ShadowRun | None,
        backtest_run: BacktestRun | None,
    ) -> list[dict[str, Any]]:
        pending_kill_switch = self.db.scalar(
            select(func.count(KillSwitchRequest.id)).where(KillSwitchRequest.status == "pending")
        ) or 0
        return [
            {
                "code": "latest_backtest_go",
                "label": "Latest backtest recommendation is go/watch",
                "passed": backtest_run is not None and backtest_run.recommendation in {"go", "watch"},
            },
            {
                "code": "shadow_not_blocked",
                "label": "Latest shadow run is not blocked",
                "passed": shadow_run is not None and shadow_run.recommendation in {"go", "watch"},
            },
            {
                "code": "shadow_risk_state_safe",
                "label": "Shadow run risk state is not RiskOff/Frozen",
                "passed": shadow_run is not None and shadow_run.risk_state not in {"RiskOff", "Frozen"},
            },
            {
                "code": "kill_switch_queue_clear",
                "label": "No pending kill-switch approvals",
                "passed": int(pending_kill_switch) == 0,
            },
        ]

    def _build_evidence_summary(
        self,
        *,
        shadow_run: ShadowRun | None,
        backtest_run: BacktestRun | None,
    ) -> dict[str, Any]:
        return {
            "latest_backtest": self._serialize_linked_run(backtest_run),
            "latest_shadow_run": self._serialize_linked_run(shadow_run),
        }

    def _serialize_linked_run(self, run: BacktestRun | ShadowRun | None) -> dict[str, Any] | None:
        if run is None:
            return None
        payload = {
            "id": str(run.id),
            "run_name": run.run_name,
            "created_at": run.created_at.isoformat(),
        }
        if isinstance(run, BacktestRun):
            payload["recommendation"] = run.recommendation
            payload["window_end"] = run.window_end.isoformat()
        if isinstance(run, ShadowRun):
            payload["recommendation"] = run.recommendation
            payload["risk_state"] = run.risk_state
        return payload

    def _has_failed_checklist(self, checklist: Any) -> bool:
        if not isinstance(checklist, list):
            return True
        return any(not bool(item.get("passed")) for item in checklist if isinstance(item, dict))

    def _require_review(self, review_id: uuid.UUID) -> LaunchReview:
        review = self.get_review(review_id)
        if review is None:
            raise ValueError(f"LaunchReview {review_id} not found")
        return review

    def _write_audit(self, *, review: LaunchReview, action: str, result: str) -> None:
        if self.audit_service is None:
            return
        self.audit_service.safe_write_event(
            AuditEvent(
                actor_id=review.reviewed_by or review.requested_by,
                actor_type="user",
                object_type="launch_review",
                object_id=str(review.id),
                action=action,
                result=result,
                event_payload={
                    "title": review.title,
                    "stage_name": review.stage_name,
                    "status": review.status,
                },
            ),
            session=self.db,
        )
