from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any

from sqlalchemy import func, select

from app.config import Settings, get_settings
from db.models import DataQualityResult, Market, MarketSnapshot
from db.session import session_scope
from services.dq.contracts import DQCheckResult

ACTIVE_MARKET_STATUSES = ("active_accepting_orders", "active_open", "active_paused")


def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _decimal_to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _snapshot_to_payload(snapshot: MarketSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "snapshot_time": _ensure_utc_datetime(snapshot.snapshot_time).isoformat(),
        "best_bid_no": _decimal_to_float(snapshot.best_bid_no),
        "best_ask_no": _decimal_to_float(snapshot.best_ask_no),
        "best_bid_yes": _decimal_to_float(snapshot.best_bid_yes),
        "best_ask_yes": _decimal_to_float(snapshot.best_ask_yes),
        "last_trade_price_no": _decimal_to_float(snapshot.last_trade_price_no),
        "spread": _decimal_to_float(snapshot.spread),
        "top_of_book_depth": _decimal_to_float(snapshot.top_of_book_depth),
        "cumulative_depth_at_target_size": _decimal_to_float(snapshot.cumulative_depth_at_target_size),
        "trade_count": snapshot.trade_count,
        "traded_volume": _decimal_to_float(snapshot.traded_volume),
        "last_trade_age_seconds": snapshot.last_trade_age_seconds,
    }


def _check_to_payload(check: DQCheckResult) -> dict[str, Any]:
    return {
        "code": check.code,
        "status": check.status,
        "severity": check.severity,
        "message": check.message,
        "blocking": check.blocking,
        "reason_code": check.reason_code,
        "details": check.details,
    }


def _mid_price(snapshot: MarketSnapshot | None) -> float | None:
    if snapshot is None:
        return None
    if snapshot.best_bid_no is not None and snapshot.best_ask_no is not None:
        return float((Decimal(snapshot.best_bid_no) + Decimal(snapshot.best_ask_no)) / Decimal("2"))
    if snapshot.last_trade_price_no is not None:
        return float(snapshot.last_trade_price_no)
    return None


class MarketDataQualityService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def evaluate_markets(
        self,
        *,
        checked_at: datetime,
        market_limit: int | None = None,
    ) -> dict[str, Any]:
        effective_market_limit = market_limit
        if effective_market_limit is None or effective_market_limit <= 0:
            effective_market_limit = self._settings.dq_market_limit
            if effective_market_limit <= 0:
                effective_market_limit = self._settings.ingest_snapshot_market_limit
            if effective_market_limit <= 0:
                effective_market_limit = None

        stats: dict[str, Any] = {
            "checked_at": checked_at.isoformat(),
            "selected_markets": 0,
            "created": 0,
            "skipped_existing": 0,
            "pass": 0,
            "warn": 0,
            "fail": 0,
            "alerts_emitted": 0,
            "alert_samples": [],
        }

        with session_scope() as session:
            stmt = (
                select(Market)
                .where(Market.market_status.in_(ACTIVE_MARKET_STATUSES))
                .order_by(Market.source_updated_at.desc(), Market.updated_at.desc())
            )
            if effective_market_limit:
                stmt = stmt.limit(effective_market_limit)

            markets = session.scalars(stmt).all()
            stats["selected_markets"] = len(markets)

            if not markets:
                return stats

            market_ids = [market.id for market in markets]

            existing_market_ids = set(
                session.scalars(
                    select(DataQualityResult.market_ref_id).where(
                        DataQualityResult.checked_at == checked_at,
                        DataQualityResult.rule_version == self._settings.dq_rule_version,
                        DataQualityResult.market_ref_id.in_(market_ids),
                    )
                ).all()
            )

            # Batch load snapshots for all markets to avoid N+1 queries
            snapshots_query = (
                select(MarketSnapshot)
                .where(MarketSnapshot.market_ref_id.in_(market_ids))
                .order_by(MarketSnapshot.market_ref_id, MarketSnapshot.snapshot_time.desc())
            )
            all_snapshots = session.scalars(snapshots_query).all()

            # Group snapshots by market_id
            snapshots_by_market: dict[Any, list[MarketSnapshot]] = {}
            for snapshot in all_snapshots:
                if snapshot.market_ref_id not in snapshots_by_market:
                    snapshots_by_market[snapshot.market_ref_id] = []
                if len(snapshots_by_market[snapshot.market_ref_id]) < 2:
                    snapshots_by_market[snapshot.market_ref_id].append(snapshot)

            for market in markets:
                if market.id in existing_market_ids:
                    stats["skipped_existing"] += 1
                    continue

                market_snapshots = snapshots_by_market.get(market.id, [])
                latest_snapshot = market_snapshots[0] if market_snapshots else None
                previous_snapshot = market_snapshots[1] if len(market_snapshots) > 1 else None

                checks = self._evaluate_market_checks(
                    session=session,
                    market=market,
                    checked_at=checked_at,
                    latest_snapshot=latest_snapshot,
                    previous_snapshot=previous_snapshot,
                )

                failure_count = sum(1 for check in checks if check.blocking)
                warning_count = sum(1 for check in checks if check.severity == "warning")
                if failure_count > 0:
                    status = "fail"
                elif warning_count > 0:
                    status = "warn"
                else:
                    status = "pass"

                score = max(0.0, 1.0 - (failure_count * 0.2) - (warning_count * 0.05))
                blocking_reason_codes = sorted(
                    {
                        check.reason_code
                        for check in checks
                        if check.blocking and check.reason_code is not None
                    }
                )
                warning_reason_codes = sorted(
                    {
                        check.reason_code
                        for check in checks
                        if (not check.blocking) and check.reason_code is not None
                    }
                )

                result_details = {
                    "summary": {
                        "status": status,
                        "blocking": failure_count > 0,
                        "failure_count": failure_count,
                        "warning_count": warning_count,
                        "market_status": market.market_status,
                    },
                    "checks": [_check_to_payload(check) for check in checks],
                    "blocking_reason_codes": blocking_reason_codes,
                    "warning_reason_codes": warning_reason_codes,
                    "latest_snapshot": _snapshot_to_payload(latest_snapshot),
                    "previous_snapshot": _snapshot_to_payload(previous_snapshot),
                    "thresholds": {
                        "snapshot_stale_after_seconds": self._settings.dq_snapshot_stale_after_seconds,
                        "source_stale_after_seconds": self._settings.dq_source_stale_after_seconds,
                        "max_mid_price_jump_abs": self._settings.dq_max_mid_price_jump_abs,
                        "snapshot_future_tolerance_seconds": self._settings.dq_snapshot_future_tolerance_seconds,
                    },
                }

                session.add(
                    DataQualityResult(
                        market_ref_id=market.id,
                        checked_at=checked_at,
                        status=status,
                        score=score,
                        failure_count=failure_count,
                        result_details=result_details,
                        rule_version=self._settings.dq_rule_version,
                    )
                )
                stats["created"] += 1
                stats[status] += 1

                if status != "pass":
                    stats["alerts_emitted"] += 1
                    stats["alert_samples"].append(
                        {
                            "market_id": market.market_id,
                            "status": status,
                            "blocking_reason_codes": blocking_reason_codes,
                        }
                    )

        return stats

    def _evaluate_market_checks(
        self,
        *,
        session,
        market: Market,
        checked_at: datetime,
        latest_snapshot: MarketSnapshot | None,
        previous_snapshot: MarketSnapshot | None,
    ) -> list[DQCheckResult]:
        checks: list[DQCheckResult] = []
        checks.extend(self._check_market_required_fields(market))
        checks.extend(self._check_market_time_logic(market))
        checks.extend(self._check_source_freshness(market, checked_at))
        checks.extend(self._check_duplicate_signature(session, market))

        if latest_snapshot is None:
            checks.append(
                DQCheckResult(
                    code="DQ_SNAPSHOT_MISSING",
                    status="fail",
                    severity="error",
                    message="未找到最新快照，无法判断当前盘口状态。",
                    blocking=True,
                    reason_code="REJ_DATA_STALE",
                )
            )
            return checks

        checks.extend(self._check_snapshot_required_fields(latest_snapshot))
        checks.extend(self._check_snapshot_time_logic(market, latest_snapshot, checked_at))
        checks.extend(self._check_snapshot_staleness(latest_snapshot, checked_at))
        checks.extend(self._check_snapshot_consistency(latest_snapshot))
        checks.extend(self._check_snapshot_jump(latest_snapshot, previous_snapshot))
        return checks

    @staticmethod
    def _check_market_required_fields(market: Market) -> list[DQCheckResult]:
        missing_critical: list[str] = []
        warnings: list[DQCheckResult] = []

        if not market.question:
            missing_critical.append("question")
        if not market.description:
            missing_critical.append("description")
        if market.close_time is None:
            missing_critical.append("close_time")
        if not market.outcomes:
            missing_critical.append("outcomes")
        if not market.clob_token_ids:
            missing_critical.append("clob_token_ids")

        if market.open_time is None:
            warnings.append(
                DQCheckResult(
                    code="DQ_MARKET_OPEN_TIME_MISSING",
                    status="warn",
                    severity="warning",
                    message="市场缺少 open_time，时间线可解释性不足。",
                    blocking=False,
                )
            )
        if market.creation_time is None:
            warnings.append(
                DQCheckResult(
                    code="DQ_MARKET_CREATION_TIME_MISSING",
                    status="warn",
                    severity="warning",
                    message="市场缺少 creation_time，研究回放可能无法精准复盘。",
                    blocking=False,
                )
            )

        if missing_critical:
            warnings.insert(
                0,
                DQCheckResult(
                    code="DQ_MARKET_REQUIRED_FIELDS_MISSING",
                    status="fail",
                    severity="error",
                    message="市场关键字段缺失。",
                    blocking=True,
                    reason_code="REJ_DATA_INCOMPLETE",
                    details={"missing_fields": missing_critical},
                ),
            )
        return warnings

    @staticmethod
    def _check_market_time_logic(market: Market) -> list[DQCheckResult]:
        checks: list[DQCheckResult] = []
        creation_time = _ensure_utc_datetime(market.creation_time)
        open_time = _ensure_utc_datetime(market.open_time)
        close_time = _ensure_utc_datetime(market.close_time)
        resolution_time = _ensure_utc_datetime(market.resolution_time)

        if creation_time and open_time and creation_time > open_time:
            checks.append(
                DQCheckResult(
                    code="DQ_MARKET_CREATION_AFTER_OPEN",
                    status="fail",
                    severity="error",
                    message="creation_time 晚于 open_time。",
                    blocking=True,
                    reason_code="REJ_DATA_LEAK_RISK",
                )
            )
        if open_time and close_time and open_time > close_time:
            checks.append(
                DQCheckResult(
                    code="DQ_MARKET_OPEN_AFTER_CLOSE",
                    status="fail",
                    severity="error",
                    message="open_time 晚于 close_time。",
                    blocking=True,
                    reason_code="REJ_DATA_LEAK_RISK",
                )
            )
        if resolution_time and creation_time and resolution_time < creation_time:
            checks.append(
                DQCheckResult(
                    code="DQ_MARKET_RESOLUTION_BEFORE_CREATION",
                    status="fail",
                    severity="error",
                    message="resolution_time 早于 creation_time。",
                    blocking=True,
                    reason_code="REJ_DATA_LEAK_RISK",
                )
            )
        return checks

    def _check_source_freshness(self, market: Market, checked_at: datetime) -> list[DQCheckResult]:
        source_updated_at = _ensure_utc_datetime(market.source_updated_at)
        if source_updated_at is None:
            return [
                DQCheckResult(
                    code="DQ_SOURCE_UPDATED_AT_MISSING",
                    status="warn",
                    severity="warning",
                    message="市场缺少 source_updated_at，无法判断上游元数据新鲜度。",
                    blocking=False,
                )
            ]

        age_seconds = (checked_at - source_updated_at).total_seconds()
        if age_seconds > self._settings.dq_source_stale_after_seconds:
            return [
                DQCheckResult(
                    code="DQ_SOURCE_STALE",
                    status="warn",
                    severity="warning",
                    message="市场元数据距离最新更新时间过久，建议结合快照结果复核。",
                    blocking=False,
                    reason_code="REJ_DATA_STALE",
                    details={"age_seconds": int(age_seconds)},
                )
            ]
        return []

    @staticmethod
    def _check_duplicate_signature(session, market: Market) -> list[DQCheckResult]:
        if market.event_id is None or market.close_time is None:
            return []

        duplicate_count = session.scalar(
            select(func.count())
            .select_from(Market)
            .where(
                Market.id != market.id,
                Market.event_id == market.event_id,
                Market.question == market.question,
                Market.close_time == market.close_time,
                Market.market_status.in_(ACTIVE_MARKET_STATUSES),
            )
        )
        if duplicate_count and duplicate_count > 0:
            return [
                DQCheckResult(
                    code="DQ_DUPLICATE_MARKET_SIGNATURE",
                    status="warn",
                    severity="warning",
                    message="检测到同 event/question/close_time 组合的重复市场签名。",
                    blocking=False,
                    reason_code="REJ_DATA_ANOMALY",
                    details={"duplicate_count": duplicate_count + 1},
                )
            ]
        return []

    @staticmethod
    def _check_snapshot_required_fields(snapshot: MarketSnapshot) -> list[DQCheckResult]:
        missing_fields: list[str] = []
        for field_name in (
            "best_bid_no",
            "best_ask_no",
            "best_bid_yes",
            "best_ask_yes",
            "spread",
            "top_of_book_depth",
            "cumulative_depth_at_target_size",
            "traded_volume",
        ):
            if getattr(snapshot, field_name) is None:
                missing_fields.append(field_name)

        if not missing_fields:
            return []
        return [
            DQCheckResult(
                code="DQ_SNAPSHOT_REQUIRED_FIELDS_MISSING",
                status="fail",
                severity="error",
                message="最新快照缺少关键字段。",
                blocking=True,
                reason_code="REJ_DATA_INCOMPLETE",
                details={"missing_fields": missing_fields},
            )
        ]

    def _check_snapshot_staleness(
        self,
        snapshot: MarketSnapshot,
        checked_at: datetime,
    ) -> list[DQCheckResult]:
        snapshot_time = _ensure_utc_datetime(snapshot.snapshot_time)
        if snapshot_time is None:
            return [
                DQCheckResult(
                    code="DQ_SNAPSHOT_TIME_MISSING",
                    status="fail",
                    severity="error",
                    message="最新快照缺少 snapshot_time。",
                    blocking=True,
                    reason_code="REJ_DATA_STALE",
                )
            ]

        age_seconds = (checked_at - snapshot_time).total_seconds()
        if age_seconds > self._settings.dq_snapshot_stale_after_seconds:
            return [
                DQCheckResult(
                    code="DQ_SNAPSHOT_STALE",
                    status="fail",
                    severity="error",
                    message="最新快照已超过允许新鲜度阈值。",
                    blocking=True,
                    reason_code="REJ_DATA_STALE",
                    details={"age_seconds": int(age_seconds)},
                )
            ]
        return []

    def _check_snapshot_time_logic(
        self,
        market: Market,
        snapshot: MarketSnapshot,
        checked_at: datetime,
    ) -> list[DQCheckResult]:
        checks: list[DQCheckResult] = []
        snapshot_time = _ensure_utc_datetime(snapshot.snapshot_time)
        close_time = _ensure_utc_datetime(market.close_time)
        tolerance_seconds = self._settings.dq_snapshot_future_tolerance_seconds

        if snapshot_time is not None:
            delta_seconds = (snapshot_time - checked_at).total_seconds()
            if delta_seconds > tolerance_seconds:
                checks.append(
                    DQCheckResult(
                        code="DQ_SNAPSHOT_AFTER_CHECKED_AT",
                        status="fail",
                        severity="error",
                        message="快照时间晚于 DQ 检查时间，存在未来数据泄漏风险。",
                        blocking=True,
                        reason_code="REJ_DATA_LEAK_RISK",
                        details={"delta_seconds": int(delta_seconds)},
                    )
                )
        if close_time and snapshot_time and snapshot_time > close_time and market.market_status in ACTIVE_MARKET_STATUSES:
            checks.append(
                DQCheckResult(
                    code="DQ_ACTIVE_MARKET_SNAPSHOT_AFTER_CLOSE",
                    status="fail",
                    severity="error",
                    message="活跃市场的最新快照时间晚于 close_time。",
                    blocking=True,
                    reason_code="REJ_DATA_LEAK_RISK",
                )
            )
        return checks

    def _check_snapshot_consistency(self, snapshot: MarketSnapshot) -> list[DQCheckResult]:
        checks: list[DQCheckResult] = []
        if snapshot.best_bid_no is not None and snapshot.best_ask_no is not None and snapshot.best_bid_no > snapshot.best_ask_no:
            checks.append(
                DQCheckResult(
                    code="DQ_NO_BOOK_CROSSED",
                    status="fail",
                    severity="error",
                    message="NO 盘口出现 bid 大于 ask 的 crossed book。",
                    blocking=True,
                    reason_code="REJ_DATA_ANOMALY",
                )
            )
        if snapshot.best_bid_yes is not None and snapshot.best_ask_yes is not None and snapshot.best_bid_yes > snapshot.best_ask_yes:
            checks.append(
                DQCheckResult(
                    code="DQ_YES_BOOK_CROSSED",
                    status="fail",
                    severity="error",
                    message="YES 盘口出现 bid 大于 ask 的 crossed book。",
                    blocking=True,
                    reason_code="REJ_DATA_ANOMALY",
                )
            )
        if snapshot.spread is not None and snapshot.spread < 0:
            checks.append(
                DQCheckResult(
                    code="DQ_NEGATIVE_SPREAD",
                    status="fail",
                    severity="error",
                    message="spread 为负值。",
                    blocking=True,
                    reason_code="REJ_DATA_ANOMALY",
                )
            )
        for field_name in ("top_of_book_depth", "cumulative_depth_at_target_size", "traded_volume"):
            value = getattr(snapshot, field_name)
            if value is not None and value < 0:
                checks.append(
                    DQCheckResult(
                        code=f"DQ_NEGATIVE_{field_name.upper()}",
                        status="fail",
                        severity="error",
                        message=f"{field_name} 为负值。",
                        blocking=True,
                        reason_code="REJ_DATA_ANOMALY",
                    )
                )

        if snapshot.spread is not None and float(snapshot.spread) > self._settings.dq_warning_spread_threshold:
            checks.append(
                DQCheckResult(
                    code="DQ_SPREAD_WIDE_WARNING",
                    status="warn",
                    severity="warning",
                    message="当前 spread 偏宽，建议在后续流动性筛选中重点关注。",
                    blocking=False,
                    details={"spread": float(snapshot.spread)},
                )
            )
        return checks

    def _check_snapshot_jump(
        self,
        latest_snapshot: MarketSnapshot,
        previous_snapshot: MarketSnapshot | None,
    ) -> list[DQCheckResult]:
        if previous_snapshot is None:
            return []

        latest_mid = _mid_price(latest_snapshot)
        previous_mid = _mid_price(previous_snapshot)
        if latest_mid is None or previous_mid is None:
            return []

        jump_abs = abs(latest_mid - previous_mid)
        if jump_abs > self._settings.dq_max_mid_price_jump_abs:
            return [
                DQCheckResult(
                    code="DQ_MID_PRICE_JUMP_WARNING",
                    status="warn",
                    severity="warning",
                    message="相邻两条快照的 NO 中间价跳变过大，需要人工复核。",
                    blocking=False,
                    reason_code="REJ_DATA_ANOMALY",
                    details={
                        "latest_mid_price_no": latest_mid,
                        "previous_mid_price_no": previous_mid,
                        "jump_abs": jump_abs,
                    },
                )
            ]
        return []


@lru_cache
def get_market_dq_service() -> MarketDataQualityService:
    return MarketDataQualityService(settings=get_settings())
