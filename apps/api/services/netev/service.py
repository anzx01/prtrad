"""M3 NetEV 准入评估服务"""
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.models import NetEVCandidate, CalibrationUnit, Market


class NetEVService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, market_id: uuid.UUID) -> Optional[NetEVCandidate]:
        """准入评估核心逻辑"""
        # 1. 查找市场数据
        market = self.db.get(Market, market_id)
        if not market:
            return None

        # 2. 匹配校准单元
        # 简化匹配逻辑：价格、类别和时间桶
        # 实际情况中，会有复杂的分桶逻辑将市场属性映射到具体桶中
        # 假设这里能够准确匹配到一个 CalibrationUnit
        stmt = select(CalibrationUnit).where(
            CalibrationUnit.category_code == (market.category_raw or "Uncategorized"),
            CalibrationUnit.is_active == True
        ).limit(1)
        unit = self.db.scalar(stmt)

        # 3. 计算 NetEV
        # NetEV = GrossEdge - Fee - Slippage - DisputeRisk
        gross_edge = unit.edge_estimate if unit else Decimal("0.02")
        fee_cost = Decimal("0.005")  # 模拟费率
        slippage_cost = Decimal("0.003")  # 模拟冲击成本
        dispute_discount = Decimal("0.002")  # 模拟纠纷折扣

        net_ev = gross_edge - fee_cost - slippage_cost - dispute_discount

        # 4. 做出决策
        decision = "admit" if net_ev > 0 else "reject"
        rejection_reason = None if decision == "admit" else "insufficient_ev"

        # 5. 记录并返回评估结果
        candidate = NetEVCandidate(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            calibration_unit_id=unit.id if unit else None,
            gross_edge=gross_edge,
            fee_cost=fee_cost,
            slippage_cost=slippage_cost,
            dispute_discount=dispute_discount,
            net_ev=net_ev,
            admission_decision=decision,
            rejection_reason_code=rejection_reason,
            evaluated_at=datetime.now(UTC)
        )

        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def list_candidates(self, decision: Optional[str] = None) -> List[NetEVCandidate]:
        """列出准入评估候选记录"""
        stmt = select(NetEVCandidate)
        if decision:
            stmt = stmt.where(NetEVCandidate.admission_decision == decision)
        stmt = stmt.order_by(NetEVCandidate.evaluated_at.desc())
        return list(self.db.scalars(stmt).all())
