"""Risk service for exposure aggregation and state transitions."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import NetEVCandidate, RiskExposure, RiskStateEvent, RiskThresholdConfig


RISK_STATE_ORDER = ["Normal", "Caution", "RiskOff", "Frozen"]

_DEFAULT_THRESHOLDS = {
    "utilization_caution": Decimal("0.60"),
    "utilization_risk_off": Decimal("0.80"),
    "max_positions": Decimal("50"),
}


class RiskService:
    def __init__(self, db: Session) -> None:
        self.db = db

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

        The current baseline uses `Market.category_raw` as the risk cluster and
        treats net exposure as the raw cluster sum. That is enough to support
        the M4 dashboard and state machine while keeping the logic auditable.
        """
        now = datetime.now(UTC)

        from db.models import Market  # Avoid a circular import.

        rows = self.db.execute(
            select(
                Market.category_raw.label("cluster"),
                func.count(NetEVCandidate.id).label("cnt"),
                func.sum(NetEVCandidate.net_ev).label("gross"),
            )
            .join(Market, NetEVCandidate.market_ref_id == Market.id)
            .where(NetEVCandidate.admission_decision == "admit")
            .group_by(Market.category_raw)
        ).all()

        if cluster_code:
            rows = [row for row in rows if row.cluster == cluster_code]

        exposures: list[RiskExposure] = []
        for row in rows:
            cluster = row.cluster or "Uncategorized"
            limit_value = self._get_threshold(cluster, "max_exposure", Decimal("10.0"))
            gross = Decimal(str(row.gross or 0))
            net = gross
            utilization = net / limit_value if limit_value > 0 else Decimal("0")

            exposure = RiskExposure(
                id=uuid.uuid4(),
                snapshot_at=now,
                cluster_code=cluster,
                gross_exposure=gross,
                net_exposure=net,
                position_count=int(row.cnt or 0),
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
