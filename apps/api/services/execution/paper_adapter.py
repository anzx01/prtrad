from __future__ import annotations

import uuid

from db.models import TradingOrderRecord

from .contracts import ExecutionAdapterResult


class PaperExecutionAdapter:
    provider = "paper_engine"

    def execute(self, *, order: TradingOrderRecord) -> ExecutionAdapterResult:
        simulated_order_id = f"paper-{uuid.uuid4().hex[:12]}"
        return ExecutionAdapterResult(
            status="filled",
            provider=self.provider,
            provider_order_id=simulated_order_id,
            details={
                "simulated": True,
                "note": "纸交易已按当前价格完成模拟成交。",
            },
        )
