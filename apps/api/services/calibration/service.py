"""M3 校准服务"""
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.models import CalibrationUnit, Market, MarketSnapshot


class CalibrationService:
    def __init__(self, db: Session):
        self.db = db

    def list_active_units(self) -> List[CalibrationUnit]:
        """获取所有激活的校准单元"""
        return list(self.db.scalars(
            select(CalibrationUnit)
            .where(CalibrationUnit.is_active == True)
            .order_by(CalibrationUnit.category_code, CalibrationUnit.price_bucket)
        ).all())

    def get_unit(self, unit_id: uuid.UUID) -> Optional[CalibrationUnit]:
        """获取特定校准单元"""
        return self.db.get(CalibrationUnit, unit_id)

    def compute_calibration(
        self,
        category_code: str,
        price_bucket: str,
        time_bucket: str,
        liquidity_tier: str = "standard",
        window_type: str = "long"
    ) -> CalibrationUnit:
        """
        计算并更新校准单元 (简化实现)
        在实际生产中，这里会涉及复杂的统计聚合逻辑
        """
        # 1. 模拟统计数据聚合 (从历史 Market/MarketSnapshot 聚合)
        # 实际逻辑应根据 category/bucket 筛选已结算市场并计算其真实期望

        # 暂时使用占位逻辑生成一个活跃的校准单元
        now = datetime.now(UTC)

        # 检查是否已存在
        stmt = select(CalibrationUnit).where(
            CalibrationUnit.category_code == category_code,
            CalibrationUnit.price_bucket == price_bucket,
            CalibrationUnit.time_bucket == time_bucket,
            CalibrationUnit.liquidity_tier == liquidity_tier,
            CalibrationUnit.window_type == window_type
        )
        unit = self.db.scalar(stmt)

        if not unit:
            unit = CalibrationUnit(
                id=uuid.uuid4(),
                category_code=category_code,
                price_bucket=price_bucket,
                time_bucket=time_bucket,
                liquidity_tier=liquidity_tier,
                window_type=window_type,
                sample_count=100,  # 模拟数据
                edge_estimate=Decimal("0.025"),  # 2.5% 理论边缘
                interval_low=Decimal("0.015"),
                interval_high=Decimal("0.035"),
                is_active=True,
                computed_at=now
            )
            self.db.add(unit)
        else:
            unit.sample_count += 10
            unit.computed_at = now

        self.db.commit()
        self.db.refresh(unit)
        return unit
