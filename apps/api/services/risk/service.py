"""Risk service for exposure aggregation and state transitions."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import RiskExposure, RiskStateEvent, RiskThresholdConfig
from services.audit import AuditEvent
from services.risk.clustering import (
    load_latest_admitted_candidates,
    load_latest_classifications,
    resolve_cluster_code,
)


RISK_STATE_ORDER = ["Normal", "Caution", "RiskOff", "Frozen"]

_DEFAULT_THRESHOLDS = {
    "utilization_caution": Decimal("0.60"),
    "utilization_risk_off": Decimal("0.80"),
    "max_exposure": Decimal("10.0"),
    "max_positions": Decimal("50"),
}

VALID_THRESHOLD_METRICS = frozenset(_DEFAULT_THRESHOLDS.keys())


class RiskService:
    def __init__(self, db: Session, audit_service: Any | None = None) -> None:
        self.db = db
        if audit_service is None:
            from services.audit import get_audit_log_service

            audit_service = get_audit_log_service()
        self.audit_service = audit_service

    def get_current_state(self) -> str:
        """Return the latest global risk state."""
        latest = self.db.scalar(
            select(RiskStateEvent).order_by(RiskStateEvent.created_at.desc()).limit(1)
        )
        return latest.to_state if latest else "Normal"

    def list_state_events(self, limit: int = 20) -> list[RiskStateEvent]:
        return list(
            self.db.scalars(
                select(RiskStateEvent)
                .order_by(RiskStateEvent.created_at.desc())
                .limit(limit)
            ).all()
        )

    def compute_exposure(self, cluster_code: Optional[str] = None) -> list[RiskExposure]:
        """
        Aggregate admitted NetEV candidates into cluster-level exposure snapshots.

        The current baseline keeps one latest NetEV record per market and
        derives clusters from structured classification data when available.
        This avoids double-counting stale candidate rows while preserving an
        auditable and easy-to-follow aggregation path.
        """
        now = datetime.now(UTC)
        latest_candidate_rows = load_latest_admitted_candidates(self.db)
        latest_classifications = load_latest_classifications(
            self.db,
            [candidate.market_ref_id for candidate, _ in latest_candidate_rows],
        )

        grouped_rows: dict[str, dict[str, Any]] = {}
        for candidate, market in latest_candidate_rows:
            cluster = resolve_cluster_code(
                market=market,
                classification_result=latest_classifications.get(candidate.market_ref_id),
            )
            if cluster_code and cluster != cluster_code:
                continue

            summary = grouped_rows.setdefault(cluster, {"gross": Decimal("0"), "count": 0})
            summary["gross"] += Decimal(str(candidate.net_ev))
            summary["count"] += 1

        exposures: list[RiskExposure] = []
        for cluster, summary in sorted(grouped_rows.items()):
            limit_value = self._get_threshold(cluster, "max_exposure", Decimal("10.0"))
            gross = summary["gross"]
            net = gross
            utilization = net / limit_value if limit_value > 0 else Decimal("0")

            exposure = RiskExposure(
                id=uuid.uuid4(),
                snapshot_at=now,
                cluster_code=cluster,
                gross_exposure=gross,
                net_exposure=net,
                position_count=int(summary["count"]),
                limit_value=limit_value,
                utilization_rate=utilization,
                is_breached=utilization
                >= self._get_threshold(cluster, "utilization_risk_off", Decimal("0.80")),
            )
            self.db.add(exposure)
            exposures.append(exposure)

        self.db.flush()
        return exposures

    def list_exposures(self, cluster_code: Optional[str] = None) -> list[RiskExposure]:
        """Return the latest exposure snapshot for each cluster."""
        subquery = (
            select(
                RiskExposure.cluster_code,
                func.max(RiskExposure.snapshot_at).label("latest"),
            )
            .group_by(RiskExposure.cluster_code)
            .subquery()
        )

        statement = select(RiskExposure).join(
            subquery,
            (RiskExposure.cluster_code == subquery.c.cluster_code)
            & (RiskExposure.snapshot_at == subquery.c.latest),
        )
        if cluster_code:
            statement = statement.where(RiskExposure.cluster_code == cluster_code)
        statement = statement.order_by(RiskExposure.cluster_code.asc())
        return list(self.db.scalars(statement).all())

    def check_and_auto_transition(self) -> Optional[RiskStateEvent]:
        """
        Auto-escalate the global state when utilization exceeds a threshold.

        This baseline only promotes the state. Recovery remains a manual step so
        the system does not flap during noisy periods.
        """
        current_state = self.get_current_state()
        exposures = self.list_exposures()

        worst_utilization = Decimal("0")
        trigger_cluster = "global"
        for exposure in exposures:
            utilization = Decimal(str(exposure.utilization_rate))
            if utilization > worst_utilization:
                worst_utilization = utilization
                trigger_cluster = exposure.cluster_code

        caution_threshold = self._get_threshold(
            "global",
            "utilization_caution",
            Decimal("0.60"),
        )
        risk_off_threshold = self._get_threshold(
            "global",
            "utilization_risk_off",
            Decimal("0.80"),
        )

        target_state = "Normal"
        if worst_utilization >= risk_off_threshold:
            target_state = "RiskOff"
        elif worst_utilization >= caution_threshold:
            target_state = "Caution"

        if RISK_STATE_ORDER.index(target_state) <= RISK_STATE_ORDER.index(current_state):
            return None

        event = RiskStateEvent(
            id=uuid.uuid4(),
            from_state=current_state,
            to_state=target_state,
            trigger_type="auto",
            trigger_metric=f"{trigger_cluster}.utilization_rate",
            trigger_value=worst_utilization,
            threshold_value=(
                caution_threshold if target_state == "Caution" else risk_off_threshold
            ),
            actor_id=None,
            notes=(
                f"Auto-triggered by cluster {trigger_cluster} "
                f"utilization={float(worst_utilization):.2%}"
            ),
            created_at=datetime.now(UTC),
        )
        self.db.add(event)
        self.db.flush()
        self._write_audit(
            object_type="risk_state",
            object_id=str(event.id),
            action="auto_transition",
            result=target_state.lower(),
            payload={
                "from_state": current_state,
                "to_state": target_state,
                "trigger_metric": event.trigger_metric,
                "trigger_value": float(worst_utilization),
            },
        )
        return event

    def list_thresholds(self) -> list[RiskThresholdConfig]:
        return list(
            self.db.scalars(
                select(RiskThresholdConfig)
                .where(RiskThresholdConfig.is_active == True)
                .order_by(
                    RiskThresholdConfig.cluster_code.asc(),
                    RiskThresholdConfig.metric_name.asc(),
                )
            ).all()
        )

    def upsert_threshold(
        self,
        *,
        cluster_code: str,
        metric_name: str,
        threshold_value: Decimal,
        created_by: str,
    ) -> RiskThresholdConfig:
        cluster = cluster_code.strip()
        metric = metric_name.strip()
        actor = created_by.strip()

        if not cluster:
            raise ValueError("cluster_code is required")
        if metric not in VALID_THRESHOLD_METRICS:
            raise ValueError(
                f"metric_name must be one of {sorted(VALID_THRESHOLD_METRICS)}"
            )
        if not actor:
            raise ValueError("created_by is required")
        if threshold_value <= 0:
            raise ValueError("threshold_value must be greater than 0")
        if metric.startswith("utilization_") and threshold_value > 1:
            raise ValueError("utilization thresholds must be between 0 and 1")

        now = datetime.now(UTC)
        threshold = self.db.scalar(
            select(RiskThresholdConfig).where(
                RiskThresholdConfig.cluster_code == cluster,
                RiskThresholdConfig.metric_name == metric,
            )
        )

        if threshold is None:
            threshold = RiskThresholdConfig(
                id=uuid.uuid4(),
                cluster_code=cluster,
                metric_name=metric,
                threshold_value=threshold_value,
                is_active=True,
                created_by=actor,
                created_at=now,
            )
            self.db.add(threshold)
        else:
            threshold.threshold_value = threshold_value
            threshold.is_active = True
            threshold.created_by = actor
            threshold.created_at = now

        self.db.flush()
        self._write_audit(
            object_type="risk_threshold",
            object_id=str(threshold.id),
            action="upsert",
            result="success",
            actor_id=actor,
            payload={
                "cluster_code": threshold.cluster_code,
                "metric_name": threshold.metric_name,
                "threshold_value": float(threshold.threshold_value),
                "is_active": threshold.is_active,
            },
        )
        return threshold

    def deactivate_threshold(self, threshold_id: uuid.UUID) -> RiskThresholdConfig:
        threshold = self.db.get(RiskThresholdConfig, threshold_id)
        if threshold is None:
            raise ValueError(f"RiskThresholdConfig {threshold_id} not found")

        threshold.is_active = False
        self.db.flush()
        self._write_audit(
            object_type="risk_threshold",
            object_id=str(threshold.id),
            action="deactivate",
            result="success",
            actor_id=threshold.created_by,
            payload={
                "cluster_code": threshold.cluster_code,
                "metric_name": threshold.metric_name,
            },
        )
        return threshold

    def _get_threshold(self, cluster: str, metric: str, default: Decimal) -> Decimal:
        config = self.db.scalar(
            select(RiskThresholdConfig).where(
                RiskThresholdConfig.cluster_code == cluster,
                RiskThresholdConfig.metric_name == metric,
                RiskThresholdConfig.is_active == True,
            )
        )
        if config:
            return Decimal(str(config.threshold_value))

        global_config = self.db.scalar(
            select(RiskThresholdConfig).where(
                RiskThresholdConfig.cluster_code == "global",
                RiskThresholdConfig.metric_name == metric,
                RiskThresholdConfig.is_active == True,
            )
        )
        if global_config:
            return Decimal(str(global_config.threshold_value))

        return _DEFAULT_THRESHOLDS.get(metric, default)

    def _write_audit(
        self,
        *,
        object_type: str,
        object_id: str,
        action: str,
        result: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> None:
        if self.audit_service is None:
            return
        self.audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type="user" if actor_id else "system",
                object_type=object_type,
                object_id=object_id,
                action=action,
                result=result,
                event_payload=payload,
            ),
            session=self.db,
        )
