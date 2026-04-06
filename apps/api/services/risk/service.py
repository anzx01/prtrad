"""风险服务：组合风险暴露计算与状态机"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.models import (
    NetEVCandidate,
    RiskExposure,
    RiskStateEvent,
    RiskThresholdConfig,
)

# 风险状态顺序（从轻到重）
RISK_STATE_ORDER = ["Normal", "Caution", "RiskOff", "Frozen"]

# 默认阈值（当数据库无配置时使用）
_DEFAULT_THRESHOLDS = {
    "utilization_caution": Decimal("0.60"),
    "utilization_risk_off": Decimal("0.80"),
    "max_positions": Decimal("50"),
}


class RiskService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_current_state(self) -> str:
        """返回当前全局风险状态，默认 Normal"""
        latest = self.db.scalar(
            select(RiskStateEvent).order_by(RiskStateEvent.created_at.desc()).limit(1)
        )
        return latest.to_state if latest else "Normal"

    def list_state_events(self, limit: int = 20) -> list[RiskStateEvent]:
        return list(
            self.db.scalars(
                select(RiskStateEvent).order_by(RiskStateEvent.created_at.desc()).limit(limit)
            ).all()
        )

    # ------------------------------------------------------------------
    # 暴露计算
    # ------------------------------------------------------------------

    def compute_exposure(self, cluster_code: Optional[str] = None) -> list[RiskExposure]:
        """
        从 NetEVCandidate(admit) 按 cluster_code 聚合暴露，写入快照，返回结果列表。
        cluster_code 对应 market.category_raw（简化实现：用 rejection_reason_code 首段或 category 作为簇）
        """
        now = datetime.now(UTC)

        # 聚合：按 category_code 统计 admit 候选
        from db.models import Market  # 避免循环导入
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
            rows = [r for r in rows if r.cluster == cluster_code]

        exposures: list[RiskExposure] = []
        for row in rows:
            c = row.cluster or "Uncategorized"
            limit_val = self._get_threshold(c, "max_exposure", Decimal("10.0"))
            gross = Decimal(str(row.gross or 0))
            net = gross  # 简化：净=总（实际应做相关性去重）
            utilization = net / limit_val if limit_val > 0 else Decimal("0")

            exp = RiskExposure(
                id=uuid.uuid4(),
                snapshot_at=now,
                cluster_code=c,
                gross_exposure=gross,
                net_exposure=net,
                position_count=int(row.cnt or 0),
                limit_value=limit_val,
                utilization_rate=utilization,
                is_breached=utilization >= self._get_threshold(c, "utilization_risk_off", Decimal("0.80")),
            )
            self.db.add(exp)
            exposures.append(exp)

        self.db.flush()
        return exposures

    def list_exposures(self, cluster_code: Optional[str] = None) -> list[RiskExposure]:
        """返回每个簇最新一条快照"""
        sub = (
            select(
                RiskExposure.cluster_code,
                func.max(RiskExposure.snapshot_at).label("latest"),
            ).group_by(RiskExposure.cluster_code)
        ).subquery()

        stmt = select(RiskExposure).join(
            sub,
            (RiskExposure.cluster_code == sub.c.cluster_code)
            & (RiskExposure.snapshot_at == sub.c.latest),
        )
        if cluster_code:
            stmt = stmt.where(RiskExposure.cluster_code == cluster_code)
        return list(self.db.scalars(stmt).all())

    # ------------------------------------------------------------------
    # 自动状态迁移
    # ------------------------------------------------------------------

    def check_and_auto_transition(self) -> Optional[RiskStateEvent]:
        """
        检查最新暴露快照，若有超阈值则自动升级风险状态。
        返回新产生的 RiskStateEvent（无变化则返回 None）。
        """
        current = self.get_current_state()
        exposures = self.list_exposures()

        worst_utilization = Decimal("0")
        trigger_cluster = "global"
        for exp in exposures:
            if Decimal(str(exp.utilization_rate)) > worst_utilization:
                worst_utilization = Decimal(str(exp.utilization_rate))
                trigger_cluster = exp.cluster_code

        caution_t = self._get_threshold("global", "utilization_caution", Decimal("0.60"))
        risk_off_t = self._get_threshold("global", "utilization_risk_off", Decimal("0.80"))

        target_state = "Normal"
        if worst_utilization >= risk_off_t:
            target_state = "RiskOff"
        elif worst_utilization >= caution_t:
            target_state = "Caution"

        # 只升级，不自动降级
        if RISK_STATE_ORDER.index(target_state) <= RISK_STATE_ORDER.index(current):
            return None

        event = RiskStateEvent(
            id=uuid.uuid4(),
            from_state=current,
            to_state=target_state,
            trigger_type="auto",
            trigger_metric=f"{trigger_cluster}.utilization_rate",
            trigger_value=worst_utilization,
            threshold_value=caution_t if target_state == "Caution" else risk_off_t,
            actor_id=None,
            notes=f"Auto-triggered by cluster {trigger_cluster} utilization={float(worst_utilization):.2%}",
        )
        self.db.add(event)
        self.db.flush()
        return event

    # ------------------------------------------------------------------
    # 阈值配置
    # ------------------------------------------------------------------

    def list_thresholds(self) -> list[RiskThresholdConfig]:
        return list(self.db.scalars(select(RiskThresholdConfig).where(RiskThresholdConfig.is_active == True)).all())

    def _get_threshold(self, cluster: str, metric: str, default: Decimal) -> Decimal:
        cfg = self.db.scalar(
            select(RiskThresholdConfig).where(
                RiskThresholdConfig.cluster_code == cluster,
                RiskThresholdConfig.metric_name == metric,
                RiskThresholdConfig.is_active == True,
            )
        )
        if cfg:
            return Decimal(str(cfg.threshold_value))
        # fallback to global
        cfg_global = self.db.scalar(
            select(RiskThresholdConfig).where(
                RiskThresholdConfig.cluster_code == "global",
                RiskThresholdConfig.metric_name == metric,
                RiskThresholdConfig.is_active == True,
            )
        )
        if cfg_global:
            return Decimal(str(cfg_global.threshold_value))
        return _DEFAULT_THRESHOLDS.get(metric, default)
