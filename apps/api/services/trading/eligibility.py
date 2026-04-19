from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from db.models import DataQualityResult, MarketSnapshot
from services.m3_helpers import decimal_or_none, midpoint_from_snapshot
from services.risk.clustering import load_latest_admitted_candidates, load_latest_classifications


ACTIVE_TRADING_MARKET_STATUSES = frozenset({"active_accepting_orders", "active_open"})


@dataclass(frozen=True)
class ExecutableMarketCandidate:
    market_ref_id: uuid.UUID
    market_id: str
    question: str
    net_ev: Decimal
    yes_token_id: str
    no_token_id: str
    entry_price: Decimal

    def to_summary(self) -> dict[str, float | str]:
        return {
            "market_id": self.market_id,
            "question": self.question,
            "net_ev": float(self.net_ev),
            "price": float(self.entry_price),
        }


def list_executable_market_candidates(
    db: Session,
    *,
    limit: int | None = None,
) -> list[ExecutableMarketCandidate]:
    latest_candidate_rows = load_latest_admitted_candidates(db)
    market_ids = [candidate.market_ref_id for candidate, _ in latest_candidate_rows]
    latest_classifications = load_latest_classifications(db, market_ids)
    latest_dq_results = _load_latest_dq_results(db, market_ids)
    latest_snapshots = _load_latest_snapshots(db, market_ids)
    now = datetime.now(UTC)

    executable: list[ExecutableMarketCandidate] = []
    for candidate, market in latest_candidate_rows:
        classification = latest_classifications.get(candidate.market_ref_id)
        dq_result = latest_dq_results.get(candidate.market_ref_id)
        snapshot = latest_snapshots.get(candidate.market_ref_id)
        token_pair = _resolve_binary_tokens(market.outcomes, market.clob_token_ids)
        entry_price = _resolve_entry_price(snapshot)

        if market.final_resolution:
            continue
        if market.market_status not in ACTIVE_TRADING_MARKET_STATUSES:
            continue
        normalized_close_time = _normalize_datetime(market.close_time)
        if normalized_close_time is not None and normalized_close_time <= now:
            continue
        if classification is None:
            continue
        if classification.classification_status != "Tagged":
            continue
        if classification.admission_bucket_code != "LIST_WHITE":
            continue
        if dq_result is None or (dq_result.status or "").lower() != "pass":
            continue
        if snapshot is None or token_pair is None or entry_price is None:
            continue

        executable.append(
            ExecutableMarketCandidate(
                market_ref_id=candidate.market_ref_id,
                market_id=market.market_id,
                question=market.question,
                net_ev=Decimal(str(candidate.net_ev)),
                yes_token_id=token_pair[0],
                no_token_id=token_pair[1],
                entry_price=entry_price,
            )
        )

    executable.sort(key=lambda item: item.net_ev, reverse=True)
    if limit is not None:
        return executable[:limit]
    return executable


def _load_latest_dq_results(db: Session, market_ids: list[uuid.UUID]) -> dict[uuid.UUID, DataQualityResult]:
    if not market_ids:
        return {}

    dq_results = db.scalars(
        select(DataQualityResult)
        .where(DataQualityResult.market_ref_id.in_(market_ids))
        .order_by(
            DataQualityResult.market_ref_id.asc(),
            desc(DataQualityResult.checked_at),
            desc(DataQualityResult.created_at),
        )
    ).all()

    latest_by_market: dict[uuid.UUID, DataQualityResult] = {}
    for dq_result in dq_results:
        latest_by_market.setdefault(dq_result.market_ref_id, dq_result)
    return latest_by_market


def _load_latest_snapshots(db: Session, market_ids: list[uuid.UUID]) -> dict[uuid.UUID, MarketSnapshot]:
    if not market_ids:
        return {}

    snapshots = db.scalars(
        select(MarketSnapshot)
        .where(MarketSnapshot.market_ref_id.in_(market_ids))
        .order_by(
            MarketSnapshot.market_ref_id.asc(),
            desc(MarketSnapshot.snapshot_time),
            desc(MarketSnapshot.created_at),
        )
    ).all()

    latest_by_market: dict[uuid.UUID, MarketSnapshot] = {}
    for snapshot in snapshots:
        latest_by_market.setdefault(snapshot.market_ref_id, snapshot)
    return latest_by_market


def _resolve_binary_tokens(outcomes: list[str] | None, token_ids: list[str] | None) -> tuple[str, str] | None:
    if not token_ids or len(token_ids) != 2:
        return None
    if not outcomes or len(outcomes) != 2:
        return None
    yes_token, no_token = token_ids[0], token_ids[1]
    if yes_token and no_token:
        return yes_token, no_token
    return None


def _resolve_entry_price(snapshot: MarketSnapshot | None) -> Decimal | None:
    if snapshot is None:
        return None

    ask_yes = decimal_or_none(snapshot.best_ask_yes)
    if ask_yes is not None:
        return ask_yes
    return midpoint_from_snapshot(snapshot)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
