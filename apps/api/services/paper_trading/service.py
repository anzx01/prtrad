from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from db.models import Market, MarketSnapshot, NetEVCandidate, PaperPosition, TradingOrderRecord
from services.m3_helpers import ONE, decimal_or_none, midpoint_from_snapshot, outcome_from_resolution, quantize_6
from services.risk.clustering import load_latest_admitted_candidates


ACTIVE_POSITION_STATUS = "open"
CLOSED_POSITION_STATUS = "closed"
DEFAULT_STRATEGY_VERSION = "paper-noshare-v1"
TRADABLE_MARKET_STATUSES = frozenset({"active_accepting_orders", "active_open"})
CLOSED_MARKET_STATUSES = frozenset({"closed", "resolved", "finalized"})


class PaperTradingService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def list_positions(self, *, status: str | None = None, limit: int = 50) -> list[PaperPosition]:
        query_limit = max(1, min(limit, 200))
        statement = select(PaperPosition).order_by(desc(PaperPosition.opened_at), desc(PaperPosition.created_at))
        if status:
            statement = statement.where(PaperPosition.status == status)
        return list(self.db.scalars(statement.limit(query_limit)).all())

    def evaluate_candidates(
        self,
        *,
        limit: int = 10,
        strategy_version: str | None = None,
    ) -> dict[str, Any]:
        query_limit = max(1, min(limit, 100))
        version = (strategy_version or "").strip() or DEFAULT_STRATEGY_VERSION
        created: list[PaperPosition] = []
        skipped: list[dict[str, str]] = []

        rows = load_latest_admitted_candidates(self.db)
        rows.sort(key=lambda row: Decimal(str(row[0].net_ev)), reverse=True)

        for candidate, market in rows[:query_limit]:
            existing = self._open_position_for_market(candidate.market_ref_id)
            if existing is not None:
                skipped.append(
                    {
                        "market_id": market.market_id,
                        "reason": "OPEN_POSITION_EXISTS",
                    }
                )
                continue

            snapshot = self._latest_snapshot(candidate.market_ref_id)
            entry_price = self._entry_price(snapshot=snapshot, side="no")
            if not self._is_market_enterable(market):
                skipped.append({"market_id": market.market_id, "reason": "MARKET_NOT_TRADABLE"})
                continue
            if snapshot is None or entry_price is None:
                skipped.append({"market_id": market.market_id, "reason": "ENTRY_PRICE_MISSING"})
                continue

            created.append(
                self._create_position(
                    market=market,
                    candidate=candidate,
                    order=None,
                    side="no",
                    entry_price=entry_price,
                    size=self._default_size(),
                    strategy_version=version,
                    opened_at=datetime.now(UTC),
                    initial_snapshot=snapshot,
                )
            )

        self.db.flush()
        return {
            "created_count": len(created),
            "skipped_count": len(skipped),
            "created": [self.serialize_position(position) for position in created],
            "skipped": skipped,
        }

    def sync_order(self, order: TradingOrderRecord) -> PaperPosition | None:
        if order.mode != "paper" or order.status != "filled" or order.market_ref_id is None:
            return None
        if order.order_price is None or order.order_size is None:
            return None

        existing_for_order = self.db.scalar(select(PaperPosition).where(PaperPosition.order_id == order.id))
        if existing_for_order is not None:
            return existing_for_order

        market = self.db.get(Market, order.market_ref_id)
        if market is None:
            return None

        existing_open = self._open_position_for_market(order.market_ref_id)
        if existing_open is not None:
            if existing_open.order_id is None:
                existing_open.order_id = order.id
                self.db.flush()
            return existing_open

        candidate = self._latest_candidate(order.market_ref_id)
        snapshot = self._latest_snapshot(order.market_ref_id)
        side = self._normalize_side(order.outcome_side)
        return self._create_position(
            market=market,
            candidate=candidate,
            order=order,
            side=side,
            entry_price=Decimal(str(order.order_price)),
            size=Decimal(str(order.order_size)),
            strategy_version=self._order_strategy_version(order),
            opened_at=order.completed_at or order.submitted_at or datetime.now(UTC),
            initial_snapshot=snapshot,
        )

    def mark_positions(self, *, auto_close: bool = True) -> dict[str, Any]:
        updated: list[PaperPosition] = []
        closed: list[PaperPosition] = []
        skipped: list[dict[str, str]] = []
        now = datetime.now(UTC)

        open_positions = self.list_positions(status=ACTIVE_POSITION_STATUS, limit=200)
        for position in open_positions:
            market = self.db.get(Market, position.market_ref_id)
            if market is None:
                skipped.append({"position_id": str(position.id), "reason": "MARKET_MISSING"})
                continue

            snapshot = self._latest_snapshot(position.market_ref_id)
            should_close = auto_close and self._should_close_market(market=market, reference_time=now)
            mark_price = self._exit_price(market=market, snapshot=snapshot, side=position.side) if should_close else self._mark_price(snapshot=snapshot, side=position.side)

            if mark_price is None:
                skipped.append({"position_id": str(position.id), "reason": "MARK_PRICE_MISSING"})
                continue

            if should_close:
                self._close_position(
                    position=position,
                    exit_price=mark_price,
                    exit_reason=self._exit_reason(market=market, reference_time=now),
                    closed_at=now,
                )
                closed.append(position)
            else:
                self._mark_position(position=position, mark_price=mark_price, mark_time=snapshot.snapshot_time if snapshot else now)
                updated.append(position)

        self.db.flush()
        return {
            "updated_count": len(updated),
            "closed_count": len(closed),
            "skipped_count": len(skipped),
            "updated": [self.serialize_position(position) for position in updated],
            "closed": [self.serialize_position(position) for position in closed],
            "skipped": skipped,
        }

    def get_summary(self) -> dict[str, Any]:
        positions = list(self.db.scalars(select(PaperPosition)).all())
        open_positions = [position for position in positions if position.status == ACTIVE_POSITION_STATUS]
        closed_positions = [position for position in positions if position.status == CLOSED_POSITION_STATUS]

        unrealized = sum(
            ((decimal_or_none(position.unrealized_pnl) or Decimal("0")) for position in open_positions),
            Decimal("0"),
        )
        realized = sum(
            ((decimal_or_none(position.realized_pnl) or Decimal("0")) for position in closed_positions),
            Decimal("0"),
        )
        entry_notional = sum(
            ((decimal_or_none(position.entry_notional) or Decimal("0")) for position in positions),
            Decimal("0"),
        )
        winners = [
            position
            for position in closed_positions
            if (decimal_or_none(position.realized_pnl) or Decimal("0")) > Decimal("0")
        ]
        win_rate = (len(winners) / len(closed_positions)) if closed_positions else 0.0

        return {
            "open_count": len(open_positions),
            "closed_count": len(closed_positions),
            "total_count": len(positions),
            "entry_notional": float(quantize_6(entry_notional)),
            "unrealized_pnl": float(quantize_6(unrealized)),
            "realized_pnl": float(quantize_6(realized)),
            "total_pnl": float(quantize_6(unrealized + realized)),
            "win_rate": win_rate,
        }

    def serialize_position(self, position: PaperPosition) -> dict[str, Any]:
        market = self.db.get(Market, position.market_ref_id)
        candidate = self.db.get(NetEVCandidate, position.candidate_id) if position.candidate_id else None

        return {
            "id": str(position.id),
            "market_ref_id": str(position.market_ref_id),
            "market_id": market.market_id if market else None,
            "question": market.question if market else None,
            "market_status": market.market_status if market else None,
            "final_resolution": market.final_resolution if market else None,
            "candidate_id": str(position.candidate_id) if position.candidate_id else None,
            "order_id": str(position.order_id) if position.order_id else None,
            "strategy_version": position.strategy_version,
            "side": position.side,
            "status": position.status,
            "opened_at": position.opened_at.isoformat(),
            "entry_price": float(position.entry_price),
            "size": float(position.size),
            "entry_notional": float(position.entry_notional),
            "mark_price": float(position.mark_price) if position.mark_price is not None else None,
            "mark_time": position.mark_time.isoformat() if position.mark_time else None,
            "unrealized_pnl": float(position.unrealized_pnl),
            "closed_at": position.closed_at.isoformat() if position.closed_at else None,
            "exit_price": float(position.exit_price) if position.exit_price is not None else None,
            "exit_reason": position.exit_reason,
            "realized_pnl": float(position.realized_pnl) if position.realized_pnl is not None else None,
            "net_ev": float(candidate.net_ev) if candidate is not None else None,
            "created_at": position.created_at.isoformat() if position.created_at else None,
            "updated_at": position.updated_at.isoformat() if position.updated_at else None,
        }

    def _create_position(
        self,
        *,
        market: Market,
        candidate: NetEVCandidate | None,
        order: TradingOrderRecord | None,
        side: str,
        entry_price: Decimal,
        size: Decimal,
        strategy_version: str | None,
        opened_at: datetime,
        initial_snapshot: MarketSnapshot | None,
    ) -> PaperPosition:
        normalized_side = self._normalize_side(side)
        normalized_entry = quantize_6(entry_price)
        normalized_size = size.quantize(Decimal("0.000001"))
        entry_notional = quantize_6(normalized_entry * normalized_size)
        initial_mark = self._mark_price(snapshot=initial_snapshot, side=normalized_side) or normalized_entry

        position = PaperPosition(
            id=uuid.uuid4(),
            market_ref_id=market.id,
            candidate_id=candidate.id if candidate else None,
            order_id=order.id if order else None,
            strategy_version=strategy_version,
            side=normalized_side,
            status=ACTIVE_POSITION_STATUS,
            opened_at=opened_at,
            entry_price=normalized_entry,
            size=normalized_size,
            entry_notional=entry_notional,
            mark_price=initial_mark,
            mark_time=initial_snapshot.snapshot_time if initial_snapshot else opened_at,
            unrealized_pnl=quantize_6((initial_mark - normalized_entry) * normalized_size),
            closed_at=None,
            exit_price=None,
            exit_reason=None,
            realized_pnl=None,
        )
        self.db.add(position)
        self.db.flush()
        return position

    def _mark_position(self, *, position: PaperPosition, mark_price: Decimal, mark_time: datetime) -> None:
        entry = Decimal(str(position.entry_price))
        size = Decimal(str(position.size))
        normalized_mark = quantize_6(mark_price)
        position.mark_price = normalized_mark
        position.mark_time = mark_time
        position.unrealized_pnl = quantize_6((normalized_mark - entry) * size)

    def _close_position(
        self,
        *,
        position: PaperPosition,
        exit_price: Decimal,
        exit_reason: str,
        closed_at: datetime,
    ) -> None:
        entry = Decimal(str(position.entry_price))
        size = Decimal(str(position.size))
        normalized_exit = quantize_6(exit_price)
        position.status = CLOSED_POSITION_STATUS
        position.closed_at = closed_at
        position.exit_price = normalized_exit
        position.exit_reason = exit_reason
        position.mark_price = normalized_exit
        position.mark_time = closed_at
        position.unrealized_pnl = Decimal("0")
        position.realized_pnl = quantize_6((normalized_exit - entry) * size)

    def _open_position_for_market(self, market_id: uuid.UUID) -> PaperPosition | None:
        return self.db.scalar(
            select(PaperPosition).where(
                PaperPosition.market_ref_id == market_id,
                PaperPosition.status == ACTIVE_POSITION_STATUS,
            )
        )

    def _latest_candidate(self, market_id: uuid.UUID) -> NetEVCandidate | None:
        return self.db.scalar(
            select(NetEVCandidate)
            .where(NetEVCandidate.market_ref_id == market_id)
            .order_by(desc(NetEVCandidate.evaluated_at), desc(NetEVCandidate.created_at))
            .limit(1)
        )

    def _latest_snapshot(self, market_id: uuid.UUID) -> MarketSnapshot | None:
        return self.db.scalar(
            select(MarketSnapshot)
            .where(MarketSnapshot.market_ref_id == market_id)
            .order_by(desc(MarketSnapshot.snapshot_time), desc(MarketSnapshot.created_at))
            .limit(1)
        )

    def _default_size(self) -> Decimal:
        size = Decimal(str(self.settings.trading_default_order_size)).quantize(Decimal("0.000001"))
        if size <= 0:
            return Decimal("1.000000")
        return size

    def _is_market_enterable(self, market: Market) -> bool:
        if market.final_resolution:
            return False
        if market.market_status not in TRADABLE_MARKET_STATUSES:
            return False
        close_time = self._normalize_datetime(market.close_time)
        return close_time is None or close_time > datetime.now(UTC)

    def _should_close_market(self, *, market: Market, reference_time: datetime) -> bool:
        if market.final_resolution:
            return True
        if (market.market_status or "").lower() in CLOSED_MARKET_STATUSES:
            return True
        close_time = self._normalize_datetime(market.close_time)
        return close_time is not None and close_time <= reference_time

    def _exit_reason(self, *, market: Market, reference_time: datetime) -> str:
        if market.final_resolution:
            return "resolved"
        if (market.market_status or "").lower() in CLOSED_MARKET_STATUSES:
            return "market_closed"
        close_time = self._normalize_datetime(market.close_time)
        if close_time is not None and close_time <= reference_time:
            return "expired"
        return "manual_or_mark"

    def _exit_price(self, *, market: Market, snapshot: MarketSnapshot | None, side: str) -> Decimal | None:
        settlement_price = self._settlement_price(market=market, side=side)
        if settlement_price is not None:
            return settlement_price
        return self._mark_price(snapshot=snapshot, side=side)

    def _settlement_price(self, *, market: Market, side: str) -> Decimal | None:
        yes_outcome = outcome_from_resolution(market.final_resolution)
        if yes_outcome is None:
            return None
        if self._normalize_side(side) == "yes":
            return yes_outcome
        return quantize_6(ONE - yes_outcome)

    def _entry_price(self, *, snapshot: MarketSnapshot | None, side: str) -> Decimal | None:
        if snapshot is None:
            return None
        normalized_side = self._normalize_side(side)
        if normalized_side == "yes":
            ask_yes = decimal_or_none(snapshot.best_ask_yes)
            if ask_yes is not None:
                return quantize_6(ask_yes)
            midpoint = midpoint_from_snapshot(snapshot)
            return midpoint

        ask_no = decimal_or_none(snapshot.best_ask_no)
        if ask_no is not None:
            return quantize_6(ask_no)
        last_no = decimal_or_none(snapshot.last_trade_price_no)
        if last_no is not None:
            return quantize_6(last_no)
        bid_yes = decimal_or_none(snapshot.best_bid_yes)
        if bid_yes is not None:
            return quantize_6(ONE - bid_yes)
        return None

    def _mark_price(self, *, snapshot: MarketSnapshot | None, side: str) -> Decimal | None:
        if snapshot is None:
            return None
        normalized_side = self._normalize_side(side)
        if normalized_side == "yes":
            bid_yes = decimal_or_none(snapshot.best_bid_yes)
            if bid_yes is not None:
                return quantize_6(bid_yes)
            last_no = decimal_or_none(snapshot.last_trade_price_no)
            if last_no is not None:
                return quantize_6(ONE - last_no)
            return midpoint_from_snapshot(snapshot)

        bid_no = decimal_or_none(snapshot.best_bid_no)
        if bid_no is not None:
            return quantize_6(bid_no)
        last_no = decimal_or_none(snapshot.last_trade_price_no)
        if last_no is not None:
            return quantize_6(last_no)
        midpoint = midpoint_from_snapshot(snapshot)
        if midpoint is not None:
            return quantize_6(ONE - midpoint)
        return None

    @staticmethod
    def _normalize_side(value: str | None) -> str:
        normalized = (value or "no").strip().lower()
        return "yes" if normalized == "yes" else "no"

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _order_strategy_version(order: TradingOrderRecord) -> str | None:
        details = order.execution_details
        if isinstance(details, dict):
            strategy = details.get("strategy")
            if isinstance(strategy, dict):
                allocation_mode = strategy.get("allocation_mode")
                if allocation_mode:
                    return str(allocation_mode)
        return "paper-order-v1"
