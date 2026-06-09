from __future__ import annotations

import importlib.util
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from db.models import (
    BacktestRun,
    KillSwitchRequest,
    RiskStateEvent,
    ShadowRun,
    TradingOrderRecord,
    TradingRuntimeState,
)
from services.audit import AuditEvent
from services.trading.eligibility import list_executable_market_candidates


VALID_TRADING_MODES = frozenset({"paper", "live"})


class TradingService:
    def __init__(self, db: Session, audit_service: Any | None = None) -> None:
        self.db = db
        self.settings = get_settings()
        if audit_service is None:
            from services.audit import get_audit_log_service

            audit_service = get_audit_log_service()
        self.audit_service = audit_service

    def sync_runtime(self) -> tuple[TradingRuntimeState, dict[str, Any]]:
        state = self._get_or_create_state()
        guard = self._build_guard_snapshot()
        self._auto_stop_if_needed(state, guard)
        state.last_guard_snapshot = guard
        self.db.flush()
        return state, guard

    def get_state_view(self) -> dict[str, Any]:
        state, guard = self.sync_runtime()
        return self._serialize_state(state=state, guard=guard)

    def start(self, *, mode: str, actor_id: str | None = None) -> dict[str, Any]:
        normalized_mode = (mode or "").strip().lower()
        if normalized_mode not in VALID_TRADING_MODES:
            raise ValueError(f"mode must be one of {sorted(VALID_TRADING_MODES)}")

        state, guard = self.sync_runtime()
        mode_guard = guard[normalized_mode]
        if not bool(mode_guard["ready"]):
            blockers = mode_guard.get("blockers") or []
            raise ValueError(str(blockers[0]["message"]) if blockers else "当前条件还不满足，暂时不能启动交易。")

        now = datetime.now(UTC)
        actor = (actor_id or "").strip() or "console_user"
        state.mode = normalized_mode
        state.status = "running"
        state.started_by = actor
        state.last_started_at = now
        state.last_stop_reason_code = None
        state.last_stop_reason_text = None
        state.last_stop_was_automatic = False
        state.last_guard_snapshot = guard
        self.db.flush()

        self._write_audit(
            state=state,
            action="start",
            result=normalized_mode,
            actor_id=actor,
            payload={
                "mode": normalized_mode,
                "executable_market_count": guard["executable_market_count"],
            },
        )
        return self._serialize_state(state=state, guard=guard)

    def stop(self, *, actor_id: str | None = None, reason: str | None = None) -> dict[str, Any]:
        state, guard = self.sync_runtime()
        now = datetime.now(UTC)
        actor = (actor_id or "").strip() or "console_user"
        message = (reason or "").strip() or "已手动停止交易。"

        state.status = "stopped"
        state.stopped_by = actor
        state.last_stopped_at = now
        state.last_stop_reason_code = "MANUAL_STOP"
        state.last_stop_reason_text = message
        state.last_stop_was_automatic = False
        state.last_guard_snapshot = guard
        self.db.flush()

        self._write_audit(
            state=state,
            action="stop",
            result="manual_stop",
            actor_id=actor,
            payload={"reason": message},
        )
        return self._serialize_state(state=state, guard=guard)

    def serialize_order(self, order: TradingOrderRecord | None) -> dict[str, Any] | None:
        if order is None:
            return None
        return {
            "id": str(order.id),
            "mode": order.mode,
            "status": order.status,
            "provider": order.provider,
            "market_id": order.market_id_snapshot,
            "question": order.question_snapshot,
            "outcome_side": order.outcome_side,
            "token_id": order.token_id,
            "price": float(order.order_price) if order.order_price is not None else None,
            "size": float(order.order_size) if order.order_size is not None else None,
            "notional": float(order.notional_amount) if order.notional_amount is not None else None,
            "net_ev": float(order.expected_net_ev) if order.expected_net_ev is not None else None,
            "requested_by": order.requested_by,
            "provider_order_id": order.provider_order_id,
            "failure_reason_code": order.failure_reason_code,
            "failure_reason_text": order.failure_reason_text,
            "created_at": self._serialize_datetime(order.created_at),
            "updated_at": self._serialize_datetime(order.updated_at),
            "submitted_at": self._serialize_datetime(order.submitted_at),
            "completed_at": self._serialize_datetime(order.completed_at),
        }

    def _get_or_create_state(self) -> TradingRuntimeState:
        state = self.db.scalar(
            select(TradingRuntimeState).order_by(TradingRuntimeState.created_at.asc()).limit(1)
        )
        if state is not None:
            return state

        state = TradingRuntimeState(
            id=uuid.uuid4(),
            mode="paper",
            status="stopped",
            started_by=None,
            stopped_by=None,
            last_started_at=None,
            last_stopped_at=None,
            last_stop_reason_code=None,
            last_stop_reason_text=None,
            last_stop_was_automatic=False,
            last_guard_snapshot=None,
        )
        self.db.add(state)
        self.db.flush()
        return state

    def _auto_stop_if_needed(self, state: TradingRuntimeState, guard: dict[str, Any]) -> None:
        if state.status != "running":
            return

        mode_guard = guard.get(state.mode) if state.mode in VALID_TRADING_MODES else None
        if not isinstance(mode_guard, dict) or bool(mode_guard.get("ready")):
            return

        blockers = mode_guard.get("blockers") or []
        first_blocker = blockers[0] if blockers else {"code": "TRADING_GUARD_FAILED", "message": "交易条件发生变化，系统已自动停止。"}
        now = datetime.now(UTC)
        state.status = "stopped"
        state.last_stopped_at = now
        state.last_stop_reason_code = str(first_blocker["code"])
        state.last_stop_reason_text = str(first_blocker["message"])
        state.last_stop_was_automatic = True
        self.db.flush()

        self._write_audit(
            state=state,
            action="auto_stop",
            result=str(first_blocker["code"]).lower(),
            actor_id=None,
            payload={"mode": state.mode, "reason": first_blocker["message"]},
        )

    def _build_guard_snapshot(self) -> dict[str, Any]:
        latest_backtest = self._latest_backtest_run()
        latest_shadow = self._latest_shadow_run()
        risk_state = self._current_risk_state()
        pending_kill_switch_count = self._pending_kill_switch_count()
        executable_markets = list_executable_market_candidates(self.db, limit=5)

        paper_blockers: list[dict[str, str]] = []
        live_blockers: list[dict[str, str]] = []

        if not executable_markets:
            self._append_blocker(
                paper_blockers,
                code="NO_EXECUTABLE_MARKETS",
                message="当前没有可执行市场，先不要启动交易。",
            )
            self._append_blocker(
                live_blockers,
                code="NO_EXECUTABLE_MARKETS",
                message="当前没有可执行市场，先不要启动实盘。",
            )

        if pending_kill_switch_count > 0:
            message = f"当前还有 {pending_kill_switch_count} 条待处理暂停请求，系统先不允许继续交易。"
            self._append_blocker(paper_blockers, code="PENDING_KILL_SWITCH", message=message)
            self._append_blocker(live_blockers, code="PENDING_KILL_SWITCH", message=message)

        if latest_backtest is None:
            message = "还没有最新回测结果，先跑一轮自动证据包。"
            self._append_blocker(paper_blockers, code="BACKTEST_MISSING", message=message)
            self._append_blocker(live_blockers, code="BACKTEST_MISSING", message=message)
        elif latest_backtest.recommendation == "nogo":
            message = "最新回测明确不支持继续推进，先暂停交易。"
            self._append_blocker(paper_blockers, code="BACKTEST_NOGO", message=message)
            self._append_blocker(live_blockers, code="BACKTEST_NOGO", message=message)
        elif latest_backtest.recommendation != "go":
            self._append_blocker(
                live_blockers,
                code="BACKTEST_NOT_GO",
                message="最新回测还不是 Go，当前只建议先跑纸交易。",
            )

        if latest_shadow is None:
            message = "还没有最新影子验证，先跑一轮自动证据包。"
            self._append_blocker(paper_blockers, code="SHADOW_MISSING", message=message)
            self._append_blocker(live_blockers, code="SHADOW_MISSING", message=message)
        elif latest_shadow.recommendation == "block":
            message = "最新影子验证明确要求暂停，先不要继续交易。"
            self._append_blocker(paper_blockers, code="SHADOW_BLOCK", message=message)
            self._append_blocker(live_blockers, code="SHADOW_BLOCK", message=message)
        elif latest_shadow.recommendation != "go":
            self._append_blocker(
                live_blockers,
                code="SHADOW_NOT_GO",
                message="最新影子验证还不是 Go，当前只建议先跑纸交易。",
            )

        if risk_state in {"RiskOff", "Frozen"}:
            message = f"当前风险状态是 {risk_state}，系统必须先暂停交易。"
            self._append_blocker(paper_blockers, code="RISK_STATE_BLOCKED", message=message)
            self._append_blocker(live_blockers, code="RISK_STATE_BLOCKED", message=message)
        elif risk_state != "Normal":
            self._append_blocker(
                live_blockers,
                code="RISK_STATE_NOT_NORMAL",
                message=f"当前风险状态是 {risk_state}，实盘仍需继续观察。",
            )

        for blocker in self._validate_live_execution_config():
            self._append_blocker(
                live_blockers,
                code=str(blocker["code"]),
                message=str(blocker["message"]),
            )

        live_daily_order_limit = int(self.settings.trading_live_daily_order_limit)
        live_daily_orders = self._count_live_orders_today()
        if live_daily_orders >= live_daily_order_limit:
            self._append_blocker(
                live_blockers,
                code="LIVE_DAILY_ORDER_LIMIT_REACHED",
                message=f"今天的实盘发单次数已达到上限（{live_daily_order_limit} 笔），系统今天会自动停住。",
            )

        return {
            "paper": {
                "ready": len(paper_blockers) == 0,
                "blockers": paper_blockers,
            },
            "live": {
                "ready": len(live_blockers) == 0,
                "blockers": live_blockers,
            },
            "executable_market_count": len(executable_markets),
            "executable_markets": [candidate.to_summary() for candidate in executable_markets],
            "latest_backtest": self._serialize_backtest(latest_backtest),
            "latest_shadow": self._serialize_shadow(latest_shadow),
            "risk_state": risk_state,
            "pending_kill_switch_count": pending_kill_switch_count,
            "live_mode_enabled": self.settings.trading_live_mode_enabled,
        }

    def _latest_backtest_run(self) -> BacktestRun | None:
        return self.db.scalar(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1))

    def _latest_shadow_run(self) -> ShadowRun | None:
        return self.db.scalar(select(ShadowRun).order_by(ShadowRun.created_at.desc()).limit(1))

    def _current_risk_state(self) -> str:
        latest_event = self.db.scalar(select(RiskStateEvent).order_by(RiskStateEvent.created_at.desc()).limit(1))
        return latest_event.to_state if latest_event else "Normal"

    def _pending_kill_switch_count(self) -> int:
        requests = self.db.scalars(
            select(KillSwitchRequest).where(KillSwitchRequest.status == "pending")
        ).all()
        return len(requests)

    def _latest_order(self) -> TradingOrderRecord | None:
        if not self._has_table("trading_order_records"):
            return None
        return self.db.scalar(
            select(TradingOrderRecord)
            .order_by(desc(TradingOrderRecord.created_at), desc(TradingOrderRecord.updated_at))
            .limit(1)
        )

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

    def _serialize_state(self, *, state: TradingRuntimeState, guard: dict[str, Any]) -> dict[str, Any]:
        headline, description = self._build_summary(state=state, guard=guard)
        return {
            "id": str(state.id),
            "status": state.status,
            "mode": state.mode,
            "started_by": state.started_by,
            "stopped_by": state.stopped_by,
            "last_started_at": self._serialize_datetime(state.last_started_at),
            "last_stopped_at": self._serialize_datetime(state.last_stopped_at),
            "last_stop_reason_code": state.last_stop_reason_code,
            "last_stop_reason_text": state.last_stop_reason_text,
            "last_stop_was_automatic": bool(state.last_stop_was_automatic),
            "paper": guard["paper"],
            "live": guard["live"],
            "executable_market_count": guard["executable_market_count"],
            "executable_markets": guard["executable_markets"],
            "latest_backtest": guard["latest_backtest"],
            "latest_shadow": guard["latest_shadow"],
            "risk_state": guard["risk_state"],
            "pending_kill_switch_count": guard["pending_kill_switch_count"],
            "live_mode_enabled": guard["live_mode_enabled"],
            "headline": headline,
            "description": description,
            "latest_order": self.serialize_order(self._latest_order()),
            "updated_at": self._serialize_datetime(state.updated_at or state.created_at)
            or self._serialize_datetime(datetime.now(UTC)),
        }

    def _build_summary(self, *, state: TradingRuntimeState, guard: dict[str, Any]) -> tuple[str, str]:
        if state.status == "running":
            if state.mode == "live":
                return (
                    "实盘闸门已开启",
                    "当前实盘前置条件仍然通过。只要风控、回测和影子验证继续满足，系统就不会主动停机。",
                )
            return (
                "纸交易运行中",
                "系统会按纸交易模式持续观察可执行市场。需要继续试跑时，直接再点一次“开始纸交易”。",
            )

        if state.last_stop_was_automatic and state.last_stop_reason_text:
            return ("交易已自动停止", state.last_stop_reason_text)

        if bool(guard["live"]["ready"]):
            return ("可以启动实盘", "当前实盘前置条件已经满足；如果你已经接好外部执行器，可以开启实盘闸门。")

        if bool(guard["paper"]["ready"]):
            return ("可以先启动纸交易", "当前适合先用纸交易继续观察，等回测和影子验证都到 Go 再考虑实盘。")

        blockers = guard["paper"]["blockers"] or guard["live"]["blockers"] or []
        message = str(blockers[0]["message"]) if blockers else "当前还不适合启动交易。"
        return ("当前先不要启动交易", message)

    def _serialize_backtest(self, run: BacktestRun | None) -> dict[str, Any] | None:
        if run is None:
            return None
        return {
            "id": str(run.id),
            "run_name": run.run_name,
            "recommendation": run.recommendation,
            "created_at": self._serialize_datetime(run.created_at),
        }

    def _serialize_shadow(self, run: ShadowRun | None) -> dict[str, Any] | None:
        if run is None:
            return None
        return {
            "id": str(run.id),
            "run_name": run.run_name,
            "recommendation": run.recommendation,
            "risk_state": run.risk_state,
            "created_at": self._serialize_datetime(run.created_at),
        }

    def _write_audit(
        self,
        *,
        state: TradingRuntimeState,
        action: str,
        result: str,
        actor_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        if self.audit_service is None:
            return
        self.audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type="user" if actor_id else "system",
                object_type="trading_runtime",
                object_id=str(state.id),
                action=action,
                result=result,
                event_payload=payload,
            ),
            session=self.db,
        )

    @staticmethod
    def _append_blocker(blockers: list[dict[str, str]], *, code: str, message: str) -> None:
        blockers.append({"code": code, "message": message})

    @staticmethod
    def _serialize_datetime(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    def _has_table(self, table_name: str) -> bool:
        try:
            bind = self.db.get_bind()
            return inspect(bind).has_table(table_name)
        except SQLAlchemyError:
            return False

    def _validate_live_execution_config(self) -> list[dict[str, str]]:
        blockers: list[dict[str, str]] = []

        if not self.settings.trading_live_mode_enabled:
            blockers.append(
                {
                    "code": "LIVE_MODE_DISABLED",
                    "message": "当前还没有开启实盘权限，先用纸交易。",
                }
            )
            return blockers

        if importlib.util.find_spec("py_clob_client_v2") is None:
            blockers.append(
                {
                    "code": "LIVE_SDK_UNAVAILABLE",
                    "message": "实盘 SDK 还没安装好，请先安装 `py_clob_client_v2`。",
                }
            )

        if not (self.settings.trading_live_private_key or "").strip():
            blockers.append(
                {
                    "code": "LIVE_PRIVATE_KEY_MISSING",
                    "message": "还没配置实盘私钥，请先补齐 `TRADING_LIVE_PRIVATE_KEY`。",
                }
            )

        signature_type = int(self.settings.trading_live_signature_type)
        if signature_type not in {0, 1, 2, 3}:
            blockers.append(
                {
                    "code": "LIVE_SIGNATURE_TYPE_INVALID",
                    "message": "`TRADING_LIVE_SIGNATURE_TYPE` 只能是 0、1、2、3 之一。",
                }
            )
        elif signature_type != 0 and not (self.settings.trading_live_funder_address or "").strip():
            blockers.append(
                {
                    "code": "LIVE_FUNDER_MISSING",
                    "message": "当前签名类型需要显式提供 funder 地址。",
                }
            )

        bankroll_fraction = float(self.settings.trading_live_bankroll_fraction)
        if bankroll_fraction <= 0 or bankroll_fraction > 1:
            blockers.append(
                {
                    "code": "LIVE_BANKROLL_FRACTION_INVALID",
                    "message": "`TRADING_LIVE_BANKROLL_FRACTION` 必须大于 0 且不能超过 1。",
                }
            )

        min_notional = float(self.settings.trading_live_min_notional)
        max_notional = float(self.settings.trading_live_max_notional)
        if min_notional <= 0:
            blockers.append(
                {
                    "code": "LIVE_MIN_NOTIONAL_INVALID",
                    "message": "`TRADING_LIVE_MIN_NOTIONAL` 必须大于 0。",
                }
            )
        if max_notional <= 0:
            blockers.append(
                {
                    "code": "LIVE_MAX_NOTIONAL_INVALID",
                    "message": "`TRADING_LIVE_MAX_NOTIONAL` 必须大于 0。",
                }
            )
        elif max_notional < min_notional:
            blockers.append(
                {
                    "code": "LIVE_NOTIONAL_RANGE_INVALID",
                    "message": "实盘最小下单额不能大于最大下单额。",
                }
            )

        daily_limit = int(self.settings.trading_live_daily_order_limit)
        if daily_limit <= 0:
            blockers.append(
                {
                    "code": "LIVE_DAILY_ORDER_LIMIT_INVALID",
                    "message": "`TRADING_LIVE_DAILY_ORDER_LIMIT` 必须至少为 1。",
                }
            )

        poll_attempts = int(self.settings.trading_live_status_poll_attempts)
        if poll_attempts <= 0:
            blockers.append(
                {
                    "code": "LIVE_STATUS_POLL_ATTEMPTS_INVALID",
                    "message": "`TRADING_LIVE_STATUS_POLL_ATTEMPTS` 必须至少为 1。",
                }
            )

        poll_interval_seconds = float(self.settings.trading_live_status_poll_interval_seconds)
        if poll_interval_seconds < 0:
            blockers.append(
                {
                    "code": "LIVE_STATUS_POLL_INTERVAL_INVALID",
                    "message": "`TRADING_LIVE_STATUS_POLL_INTERVAL_SECONDS` 不能小于 0。",
                }
            )

        return blockers
