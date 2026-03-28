from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from sqlalchemy import select

from app.config import Settings, get_settings
from db.models import Market, MarketSnapshot
from db.session import session_scope
from services.ingest.contracts import NormalizedMarketRecord
from services.ingest.polymarket_client import (
    PolymarketClobClient,
    PolymarketGammaClient,
)


ACTIVE_MARKET_STATUSES = ("active_accepting_orders", "active_open", "active_paused")


def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_json_list(value: Any) -> list[Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, list):
            return parsed
    return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _simplify_tags(tags: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    if not tags:
        return None
    return [
        {
            "id": str(tag.get("id")) if tag.get("id") is not None else None,
            "label": tag.get("label"),
            "slug": tag.get("slug"),
        }
        for tag in tags
    ]


def _normalize_status(market: dict[str, Any]) -> str:
    if market.get("archived"):
        return "archived"
    if market.get("closed"):
        if market.get("umaResolutionStatus") == "resolved":
            return "resolved"
        return "closed"
    if market.get("active"):
        if market.get("acceptingOrders") is True:
            return "active_accepting_orders"
        return "active_open"
    return "active_paused"


def _normalize_market_record(event: dict[str, Any], market: dict[str, Any]) -> NormalizedMarketRecord | None:
    market_id = market.get("id")
    question = market.get("question")
    if market_id in (None, "") or question in (None, ""):
        return None

    tags = _simplify_tags(event.get("tags"))
    outcomes = _parse_json_list(market.get("outcomes"))
    outcome_prices = _parse_json_list(market.get("outcomePrices"))
    clob_token_ids = _parse_json_list(market.get("clobTokenIds"))

    category_raw = tags[0]["label"] if tags else event.get("title")
    if category_raw is not None:
        category_raw = str(category_raw)[:128]

    return NormalizedMarketRecord(
        market_id=str(market_id),
        event_id=str(event.get("id")) if event.get("id") is not None else None,
        condition_id=market.get("conditionId"),
        question=str(question),
        description=market.get("description"),
        resolution_criteria=market.get("resolutionSource") or event.get("resolutionSource"),
        creation_time=_parse_datetime(market.get("createdAt") or event.get("creationDate")),
        open_time=_parse_datetime(market.get("startDate") or market.get("acceptingOrdersTimestamp")),
        close_time=_parse_datetime(market.get("closedTime") or market.get("endDate")),
        resolution_time=_parse_datetime(market.get("umaEndDate")),
        final_resolution=market.get("finalResolution"),
        market_status=_normalize_status(market),
        category_raw=category_raw,
        related_tags=tags,
        outcomes=[str(item) for item in outcomes] if outcomes else None,
        clob_token_ids=[str(item) for item in clob_token_ids] if clob_token_ids else None,
        source_updated_at=_parse_datetime(market.get("updatedAt") or event.get("updatedAt")),
        source_payload={
            "event": {
                "id": str(event.get("id")) if event.get("id") is not None else None,
                "title": event.get("title"),
                "slug": event.get("slug"),
                "ticker": event.get("ticker"),
                "tags": tags or [],
                "updated_at": event.get("updatedAt"),
            },
            "market": {
                "slug": market.get("slug"),
                "condition_id": market.get("conditionId"),
                "outcomes": outcomes or [],
                "outcome_prices": outcome_prices or [],
                "clob_token_ids": clob_token_ids or [],
                "best_bid": market.get("bestBid"),
                "best_ask": market.get("bestAsk"),
                "spread": market.get("spread"),
                "last_trade_price": market.get("lastTradePrice"),
                "liquidity_clob": market.get("liquidityClob"),
                "volume_24hr_clob": market.get("volume24hrClob"),
                "volume_clob": market.get("volumeClob"),
                "accepting_orders": market.get("acceptingOrders"),
                "accepting_orders_timestamp": market.get("acceptingOrdersTimestamp"),
                "enable_order_book": market.get("enableOrderBook"),
                "order_min_size": market.get("orderMinSize"),
                "tick_size": market.get("orderPriceMinTickSize"),
                "neg_risk": market.get("negRisk"),
                "updated_at": market.get("updatedAt"),
            },
        },
    )


def _best_bid(levels: list[dict[str, Any]]) -> Decimal | None:
    prices = [_decimal_or_none(level.get("price")) for level in levels]
    prices = [price for price in prices if price is not None]
    return max(prices) if prices else None


def _best_ask(levels: list[dict[str, Any]]) -> Decimal | None:
    prices = [_decimal_or_none(level.get("price")) for level in levels]
    prices = [price for price in prices if price is not None]
    return min(prices) if prices else None


def _size_at_price(levels: list[dict[str, Any]], target_price: Decimal | None) -> Decimal:
    if target_price is None:
        return Decimal("0")
    total = Decimal("0")
    for level in levels:
        price = _decimal_or_none(level.get("price"))
        size = _decimal_or_none(level.get("size"))
        if price == target_price and size is not None:
            total += size
    return total


def _cumulative_target_depth(levels: list[dict[str, Any]], target_size: Decimal) -> Decimal:
    if target_size <= 0:
        return Decimal("0")
    remaining = target_size
    cumulative = Decimal("0")
    ordered_levels = sorted(
        levels,
        key=lambda item: _decimal_or_none(item.get("price")) or Decimal("999999"),
    )
    for level in ordered_levels:
        size = _decimal_or_none(level.get("size"))
        if size is None or size <= 0:
            continue
        fill = min(size, remaining)
        cumulative += fill
        remaining -= fill
        if remaining <= 0:
            break
    return cumulative


def _resolve_binary_tokens(outcomes: list[str] | None, token_ids: list[str] | None) -> tuple[str, str] | None:
    if not outcomes or not token_ids or len(outcomes) != 2 or len(token_ids) != 2:
        return None
    mapping = {str(label).strip().lower(): token_id for label, token_id in zip(outcomes, token_ids)}
    yes_token = mapping.get("yes")
    no_token = mapping.get("no")
    if yes_token and no_token:
        return yes_token, no_token
    return None


def _coerce_payload_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


class PolymarketIngestService:
    def __init__(
        self,
        settings: Settings,
        gamma_client: PolymarketGammaClient,
        clob_client: PolymarketClobClient,
    ) -> None:
        self._settings = settings
        self._gamma_client = gamma_client
        self._clob_client = clob_client

    def sync_markets(
        self,
        *,
        triggered_at: datetime,
        force_full_scan: bool = False,
        limit_pages: int | None = None,
    ) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "triggered_at": triggered_at.isoformat(),
            "pages": 0,
            "fetched_events": 0,
            "fetched_markets": 0,
            "created": 0,
            "updated": 0,
            "skipped_unchanged": 0,
            "skipped_invalid": 0,
            "skipped_duplicate_in_run": 0,
            "marked_inactive": 0,
        }
        seen_market_ids: set[str] = set()
        offset = 0
        page_size = self._settings.ingest_gamma_page_size

        with session_scope() as session:
            while True:
                events = self._gamma_client.list_events(
                    limit=page_size,
                    offset=offset,
                    active=True,
                    closed=False,
                    archived=False,
                )
                if not events:
                    break

                stats["pages"] += 1
                stats["fetched_events"] += len(events)

                records: list[NormalizedMarketRecord] = []
                for event in events:
                    for market in event.get("markets", []):
                        stats["fetched_markets"] += 1
                        record = _normalize_market_record(event, market)
                        if record is None:
                            stats["skipped_invalid"] += 1
                            continue
                        if record.market_id in seen_market_ids:
                            stats["skipped_duplicate_in_run"] += 1
                            continue
                        seen_market_ids.add(record.market_id)
                        records.append(record)

                existing_markets = {
                    market.market_id: market
                    for market in session.scalars(
                        select(Market).where(Market.market_id.in_([record.market_id for record in records]))
                    ).all()
                } if records else {}

                for record in records:
                    existing = existing_markets.get(record.market_id)
                    if existing is None:
                        session.add(self._build_market_model(record))
                        stats["created"] += 1
                        continue

                    should_refresh = force_full_scan
                    record_updated_at = _ensure_utc_datetime(record.source_updated_at)
                    existing_updated_at = _ensure_utc_datetime(existing.source_updated_at)
                    if record_updated_at and (
                        existing_updated_at is None or record_updated_at > existing_updated_at
                    ):
                        should_refresh = True
                    if existing.condition_id is None and record.condition_id is not None:
                        should_refresh = True
                    if not existing.clob_token_ids and record.clob_token_ids:
                        should_refresh = True

                    if not should_refresh:
                        stats["skipped_unchanged"] += 1
                        continue

                    self._apply_market_record(existing, record)
                    stats["updated"] += 1

                session.commit()

                offset += page_size
                if len(events) < page_size:
                    break
                if limit_pages is not None and stats["pages"] >= limit_pages:
                    break

            if limit_pages is None:
                active_markets = session.scalars(
                    select(Market).where(Market.market_status.in_(ACTIVE_MARKET_STATUSES))
                ).all()
                for market in active_markets:
                    if market.market_id in seen_market_ids:
                        continue
                    market.market_status = "inactive_from_feed"
                    payload = _coerce_payload_dict(market.source_payload)
                    payload["inactive_detected_at"] = triggered_at.isoformat()
                    market.source_payload = payload
                    stats["marked_inactive"] += 1
                session.commit()

        return stats

    def capture_snapshots(
        self,
        *,
        triggered_at: datetime,
        market_limit: int | None = None,
    ) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "triggered_at": triggered_at.isoformat(),
            "selected_markets": 0,
            "created": 0,
            "skipped_existing": 0,
            "skipped_missing_mapping": 0,
            "skipped_missing_order_books": 0,
        }
        target_size = Decimal(str(self._settings.ingest_snapshot_target_size))

        effective_market_limit = market_limit
        if effective_market_limit is None or effective_market_limit <= 0:
            configured_limit = self._settings.ingest_snapshot_market_limit
            effective_market_limit = configured_limit if configured_limit > 0 else None

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

            existing_snapshot_market_ids = set(
                session.scalars(
                    select(MarketSnapshot.market_ref_id).where(
                        MarketSnapshot.snapshot_time == triggered_at,
                        MarketSnapshot.market_ref_id.in_([market.id for market in markets]),
                    )
                ).all()
            ) if markets else set()

            token_ids: list[str] = []
            binary_mappings: dict[str, tuple[str, str]] = {}

            for market in markets:
                mapping = _resolve_binary_tokens(market.outcomes, market.clob_token_ids)
                if mapping is None:
                    stats["skipped_missing_mapping"] += 1
                    continue
                binary_mappings[market.market_id] = mapping
                token_ids.extend(mapping)

            token_ids = list(dict.fromkeys(token_ids))
            books = self._fetch_books(token_ids)
            books_by_token = {str(book.get("asset_id")): book for book in books if book.get("asset_id")}

            for market in markets:
                if market.id in existing_snapshot_market_ids:
                    stats["skipped_existing"] += 1
                    continue

                mapping = binary_mappings.get(market.market_id)
                if mapping is None:
                    continue

                yes_token, no_token = mapping
                yes_book = books_by_token.get(yes_token)
                no_book = books_by_token.get(no_token)
                if yes_book is None or no_book is None:
                    stats["skipped_missing_order_books"] += 1
                    continue

                no_bid = _best_bid(no_book.get("bids", []))
                no_ask = _best_ask(no_book.get("asks", []))
                no_top_depth = _size_at_price(no_book.get("bids", []), no_bid) + _size_at_price(
                    no_book.get("asks", []), no_ask
                )

                payload = _coerce_payload_dict(market.source_payload).get("market", {})
                traded_volume = payload.get("volume_24hr_clob")
                if traded_volume in (None, ""):
                    traded_volume = payload.get("volume_clob")

                session.add(
                    MarketSnapshot(
                        market_ref_id=market.id,
                        snapshot_time=triggered_at,
                        best_bid_no=no_bid,
                        best_ask_no=no_ask,
                        best_bid_yes=_best_bid(yes_book.get("bids", [])),
                        best_ask_yes=_best_ask(yes_book.get("asks", [])),
                        last_trade_price_no=_decimal_or_none(no_book.get("last_trade_price")),
                        spread=(no_ask - no_bid) if no_ask is not None and no_bid is not None else None,
                        top_of_book_depth=no_top_depth,
                        cumulative_depth_at_target_size=_cumulative_target_depth(
                            no_book.get("asks", []),
                            target_size,
                        ),
                        trade_count=None,
                        traded_volume=_decimal_or_none(traded_volume),
                        last_trade_age_seconds=None,
                    )
                )
                stats["created"] += 1

        return stats

    def _fetch_books(self, token_ids: list[str]) -> list[dict[str, Any]]:
        if not token_ids:
            return []
        books: list[dict[str, Any]] = []
        batch_size = max(1, self._settings.ingest_clob_batch_size)
        for index in range(0, len(token_ids), batch_size):
            books.extend(self._clob_client.get_order_books(token_ids[index : index + batch_size]))
        return books

    @staticmethod
    def _build_market_model(record: NormalizedMarketRecord) -> Market:
        return Market(
            market_id=record.market_id,
            event_id=record.event_id,
            condition_id=record.condition_id,
            question=record.question,
            description=record.description,
            resolution_criteria=record.resolution_criteria,
            creation_time=record.creation_time,
            open_time=record.open_time,
            close_time=record.close_time,
            resolution_time=record.resolution_time,
            final_resolution=record.final_resolution,
            market_status=record.market_status,
            category_raw=record.category_raw,
            related_tags=record.related_tags,
            outcomes=record.outcomes,
            clob_token_ids=record.clob_token_ids,
            source_payload=record.source_payload,
            source_updated_at=record.source_updated_at,
        )

    @staticmethod
    def _apply_market_record(existing: Market, record: NormalizedMarketRecord) -> None:
        existing.event_id = record.event_id
        existing.condition_id = record.condition_id
        existing.question = record.question
        existing.description = record.description
        existing.resolution_criteria = record.resolution_criteria
        existing.creation_time = record.creation_time
        existing.open_time = record.open_time
        existing.close_time = record.close_time
        existing.resolution_time = record.resolution_time
        existing.final_resolution = record.final_resolution
        existing.market_status = record.market_status
        existing.category_raw = record.category_raw
        existing.related_tags = record.related_tags
        existing.outcomes = record.outcomes
        existing.clob_token_ids = record.clob_token_ids
        existing.source_payload = record.source_payload
        existing.source_updated_at = record.source_updated_at


@lru_cache
def get_polymarket_ingest_service() -> PolymarketIngestService:
    settings = get_settings()
    return PolymarketIngestService(
        settings=settings,
        gamma_client=PolymarketGammaClient(
            base_url=settings.polymarket_gamma_api_url,
            timeout_seconds=settings.ingest_http_timeout_seconds,
        ),
        clob_client=PolymarketClobClient(
            base_url=settings.polymarket_clob_api_url,
            timeout_seconds=settings.ingest_http_timeout_seconds,
        ),
    )
