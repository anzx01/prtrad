"""Helpers for risk exposure clustering."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MarketClassificationResult, NetEVCandidate


CLUSTER_PRIORITY_FACTORS = (
    "RF_THEME_CLUSTERED",
    "RF_MACRO_CORRELATED",
    "RF_SINGLE_ASSET_CORRELATED",
    "RF_MANUAL_INTERPRETATION_REQUIRED",
    "RF_DISPUTE_TEMPLATE_SIMILAR",
)


def load_latest_admitted_candidates(
    db: Session,
) -> list[tuple[NetEVCandidate, Any]]:
    """Return the latest admitted NetEV candidate for each market."""
    from db.models import Market  # Avoid a circular import.

    candidate_rows = db.execute(
        select(NetEVCandidate, Market)
        .join(Market, NetEVCandidate.market_ref_id == Market.id)
        .order_by(
            NetEVCandidate.market_ref_id.asc(),
            NetEVCandidate.evaluated_at.desc(),
            NetEVCandidate.created_at.desc(),
        )
    ).all()

    latest_candidates_by_market: dict[uuid.UUID, tuple[NetEVCandidate, Any]] = {}
    for candidate, market in candidate_rows:
        latest_candidates_by_market.setdefault(candidate.market_ref_id, (candidate, market))

    return [
        (candidate, market)
        for candidate, market in latest_candidates_by_market.values()
        if candidate.admission_decision == "admit"
    ]


def load_latest_classifications(
    db: Session,
    market_ids: list[uuid.UUID],
) -> dict[uuid.UUID, MarketClassificationResult]:
    if not market_ids:
        return {}

    classifications = db.scalars(
        select(MarketClassificationResult)
        .where(MarketClassificationResult.market_ref_id.in_(market_ids))
        .order_by(
            MarketClassificationResult.market_ref_id.asc(),
            MarketClassificationResult.classified_at.desc(),
            MarketClassificationResult.created_at.desc(),
        )
    ).all()

    latest_by_market: dict[uuid.UUID, MarketClassificationResult] = {}
    for classification in classifications:
        latest_by_market.setdefault(classification.market_ref_id, classification)
    return latest_by_market


def resolve_cluster_code(
    *,
    market: Any,
    classification_result: MarketClassificationResult | None,
) -> str:
    if classification_result is not None:
        primary_category_code = (classification_result.primary_category_code or "").strip()
        risk_factor_code = select_cluster_factor(classification_result.result_details)
        if primary_category_code and risk_factor_code:
            return f"{primary_category_code}:{risk_factor_code}"[:64]
        if primary_category_code:
            return primary_category_code[:64]

    raw_category = (market.category_raw or "").strip()
    return (raw_category or "Uncategorized")[:64]


def select_cluster_factor(result_details: Any) -> str | None:
    if not isinstance(result_details, dict):
        return None

    summary = result_details.get("summary")
    if not isinstance(summary, dict):
        return None

    risk_factor_codes = summary.get("risk_factor_codes")
    if not isinstance(risk_factor_codes, list):
        return None

    normalized_codes = [str(code).strip() for code in risk_factor_codes if str(code).strip()]
    if not normalized_codes:
        return None

    for preferred_code in CLUSTER_PRIORITY_FACTORS:
        if preferred_code in normalized_codes:
            return preferred_code

    return sorted(normalized_codes)[0]
