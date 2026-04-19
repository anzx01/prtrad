from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Any

from sqlalchemy import desc, func, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from db.models import TradingOrderRecord
from services.audit import AuditEvent
from services.trading import TradingService
from services.trading.eligibility import ExecutableMarketCandidate, list_executable_market_candidates

from .contracts import ExecutionAdapterError
from .paper_adapter import PaperExecutionAdapter
from .polymarket_adapter import PolymarketExecutionAdapter


class ExecutionService:
    def __init__(self, db: Session, audit_service: Any | None = None) -> None:
        self.db = db
        self.settings = get_settings()
        if audit_service is None:
            from services.audit import get_audit_log_service

            audit_service = get_audit_log_service()
        self.audit_service = audit_service

    def execute_next(self, *, mode: str | None = None, actor_id: str | None = None) -> dict[str, Any]:
        self._ensure_order_storage_ready()
        trading_service = TradingService(self.db, audit_service=self.audit_service)
        state, guard = trading_service.sync_runtime()

        if state.status != "running":
            raise ValueError("交易还没有启动，请先开始纸交易或实盘。")

        resolved_mode = (mode or state.mode or "").strip().lower()
        if resolved_mode != state.mode:
            raise ValueError("当前运行模式与执行请求不一致，请先停止后再切换模式。")

        mode_guard = guard.get(resolved_mode) or {}
        if not bool(mode_guard.get("ready")):
            blockers = mode_guard.get("blockers") or []
            message = str(blockers[0]["message"]) if blockers else "当前条件还不满足，暂时不能执行订单。"
            raise ValueError(message)

        candidate = self._select_candidate()
        if candidate is None:
            raise ValueError("当前没有可执行市场，请先刷新自动证据包。")

        actor = (actor_id or "").strip() or "console_user"
        adapter = self._resolve_adapter(resolved_mode, settings=self.settings)
        if resolved_mode == "live":
            self._ensure_live_daily_order_limit_not_reached()

        order = self._create_order(
            state_id=str(state.id),
            mode=resolved_mode,
            actor_id=actor,
            candidate=candidate,
            adapter=adapter,
        )

        try:
            result = adapter.execute(order=order)
        except ExecutionAdapterError as exc:
            order.status = "failed"
            order.provider = getattr(adapter, "provider", resolved_mode)
            order.failure_reason_code = exc.code
            order.failure_reason_text = exc.message
            order.execution_details = self._merge_execution_details(
                order.execution_details,
                {
                    "simulated": resolved_mode == "paper",
                    "error_code": exc.code,
                    "error_message": exc.message,
                },
            )
            order.completed_at = datetime.now(UTC)
            self.db.flush()
            self._write_audit(
                order=order,
                action="execute_failed",
                result=exc.code.lower(),
                actor_id=actor,
            )
        else:
            order.status = result.status
            order.provider = result.provider
            order.provider_order_id = result.provider_order_id
            order.execution_details = self._merge_execution_details(order.execution_details, result.details)
            order.completed_at = datetime.now(UTC)
            self.db.flush()
            self._write_audit(
                order=order,
                action="execute_success",
                result=result.status,
                actor_id=actor,
            )

        return {
            "state": trading_service.get_state_view(),
            "order": trading_service.serialize_order(order),
        }

    def list_orders(self, *, limit: int = 10) -> list[dict[str, Any]]:
        if not self._has_table("trading_order_records"):
            return []
        query_limit = max(1, min(limit, 50))
        orders = self.db.scalars(
            select(TradingOrderRecord)
            .order_by(desc(TradingOrderRecord.created_at), desc(TradingOrderRecord.updated_at))
            .limit(query_limit)
        ).all()
        trading_service = TradingService(self.db, audit_service=self.audit_service)
        return [trading_service.serialize_order(order) for order in orders]

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        if not self._has_table("trading_order_records"):
            return None
        try:
            parsed_id = uuid.UUID(order_id)
        except ValueError:
            return None

        order = self.db.get(TradingOrderRecord, parsed_id)
        if order is None:
            return None
        trading_service = TradingService(self.db, audit_service=self.audit_service)
        return trading_service.serialize_order(order)

    def _select_candidate(self) -> ExecutableMarketCandidate | None:
        candidates = list_executable_market_candidates(self.db, limit=1)
        if not candidates:
            return None
        return candidates[0]

    def _create_order(
        self,
        *,
        state_id: str,
        mode: str,
        actor_id: str,
        candidate: ExecutableMarketCandidate,
        adapter: PaperExecutionAdapter | PolymarketExecutionAdapter,
    ) -> TradingOrderRecord:
        if mode == "live":
            size, notional, strategy_details = self._plan_live_order(candidate=candidate, adapter=adapter)
        else:
            size, notional, strategy_details = self._plan_paper_order(candidate=candidate)

        order = TradingOrderRecord(
            id=uuid.uuid4(),
            trading_runtime_state_id=uuid.UUID(state_id),
            market_ref_id=candidate.market_ref_id,
            mode=mode,
            status="pending",
            provider="paper_engine" if mode == "paper" else "polymarket_clob",
            market_id_snapshot=candidate.market_id,
            question_snapshot=candidate.question,
            outcome_side="yes",
            token_id=candidate.yes_token_id,
            order_price=candidate.entry_price,
            order_size=size,
            notional_amount=notional,
            expected_net_ev=candidate.net_ev,
            requested_by=actor_id,
            submitted_at=datetime.now(UTC),
            provider_order_id=None,
            failure_reason_code=None,
            failure_reason_text=None,
            execution_details={"strategy": strategy_details},
            completed_at=None,
        )
        self.db.add(order)
        self.db.flush()
        return order

    def _plan_paper_order(self, *, candidate: ExecutableMarketCandidate) -> tuple[Decimal, Decimal, dict[str, Any]]:
        size = Decimal(str(self.settings.trading_default_order_size)).quantize(Decimal("0.000001"))
        if size <= 0:
            raise ValueError("纸交易默认下单数量必须大于 0。")
        notional = (candidate.entry_price * size).quantize(Decimal("0.000001"))
        return (
            size,
            notional,
            {
                "allocation_mode": "fixed_size",
                "default_order_size": float(size),
            },
        )

    def _plan_live_order(
        self,
        *,
        candidate: ExecutableMarketCandidate,
        adapter: PaperExecutionAdapter | PolymarketExecutionAdapter,
    ) -> tuple[Decimal, Decimal, dict[str, Any]]:
        if not isinstance(adapter, PolymarketExecutionAdapter):
            raise ValueError("实盘模式未绑定正确的执行适配器。")

        try:
            collateral = adapter.get_collateral_snapshot()
        except ExecutionAdapterError as exc:
            raise ValueError(exc.message) from exc

        available = collateral.available or collateral.balance or collateral.allowance
        if available is None or available <= 0:
            raise ValueError("当前无法读取可用实盘余额，系统先不发单。")

        price = Decimal(str(candidate.entry_price))
        if price <= 0:
            raise ValueError("当前市场价格无效，系统先不发单。")

        fraction = Decimal(str(self.settings.trading_live_bankroll_fraction))
        min_notional = Decimal(str(self.settings.trading_live_min_notional))
        max_notional = Decimal(str(self.settings.trading_live_max_notional))
        daily_limit = int(self.settings.trading_live_daily_order_limit)
        daily_used = self._count_live_orders_today()

        target_notional = (available * fraction).quantize(Decimal("0.000001"))
        target_notional = min(target_notional, max_notional)
        if target_notional < min_notional:
            raise ValueError(
                f"当前可用实盘资金只有 {float(available):.2f}，达不到最小下单额 {float(min_notional):.2f}。"
            )

        size = (target_notional / price).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        if size <= 0:
            raise ValueError("按当前价格折算后的下单数量为 0，系统先不发单。")

        return (
            size,
            target_notional,
            {
                "allocation_mode": "bankroll_fraction",
                "bankroll_fraction": float(fraction),
                "min_notional": float(min_notional),
                "max_notional": float(max_notional),
                "balance": float(collateral.balance) if collateral.balance is not None else None,
                "allowance": float(collateral.allowance) if collateral.allowance is not None else None,
                "available_collateral": float(available),
                "daily_order_limit": daily_limit,
                "daily_orders_used_before_submit": daily_used,
                "daily_orders_remaining_after_submit": max(daily_limit - daily_used - 1, 0),
                "status_poll_attempts": int(self.settings.trading_live_status_poll_attempts),
                "status_poll_interval_seconds": float(self.settings.trading_live_status_poll_interval_seconds),
            },
        )

    @staticmethod
    def _resolve_adapter(mode: str, settings: Any | None = None) -> PaperExecutionAdapter | PolymarketExecutionAdapter:
        if mode == "paper":
            return PaperExecutionAdapter()
        return PolymarketExecutionAdapter(settings=settings)

    def _ensure_live_daily_order_limit_not_reached(self) -> None:
        daily_limit = int(self.settings.trading_live_daily_order_limit)
        used = self._count_live_orders_today()
        if used >= daily_limit:
            raise ValueError(f"今天的实盘发单次数已达到上限（{daily_limit} 笔），系统今天不再继续发单。")

    def _count_live_orders_today(self) -> int:
        if not self._has_table("trading_order_records"):
            return 0
        day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = day_start + timedelta(days=1)
        count = self.db.scalar(
            select(func.count())
            .select_from(TradingOrderRecord)
            .where(
                TradingOrderRecord.mode == "live",
                TradingOrderRecord.submitted_at >= day_start,
                TradingOrderRecord.submitted_at < next_day,
            )
        )
        return int(count or 0)

    def _write_audit(
        self,
        *,
        order: TradingOrderRecord,
        action: str,
        result: str,
        actor_id: str | None,
    ) -> None:
        if self.audit_service is None:
            return
        self.audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type="user" if actor_id else "system",
                object_type="trading_order",
                object_id=str(order.id),
                action=action,
                result=result,
                event_payload={
                    "mode": order.mode,
                    "status": order.status,
                    "provider": order.provider,
                    "market_id": order.market_id_snapshot,
                    "failure_reason_code": order.failure_reason_code,
                },
            ),
            session=self.db,
        )

    def _ensure_order_storage_ready(self) -> None:
        if self._has_table("trading_order_records"):
            return
        raise ValueError("交易订单表还没创建，请先执行 `npm run db:upgrade`。")

    @staticmethod
    def _merge_execution_details(
        base: dict[str, Any] | list[Any] | None,
        extra: dict[str, Any] | None,
    ) -> dict[str, Any] | list[Any] | None:
        if extra is None:
            return base
        if isinstance(base, dict):
            merged = dict(base)
            merged.update(extra)
            return merged
        return extra

    def _has_table(self, table_name: str) -> bool:
        try:
            bind = self.db.get_bind()
            return inspect(bind).has_table(table_name)
        except SQLAlchemyError:
            return False
