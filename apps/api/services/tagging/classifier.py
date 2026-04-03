from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from db.models import (
    Market,
    MarketClassificationResult,
    MarketReviewTask,
    MarketTagAssignment,
    MarketTagExplanation,
    TagRuleVersion,
)
from db.session import session_scope


ACTIVE_TAGGING_VERSION_STATUS = "active"
CLASSIFIABLE_MARKET_STATUSES = ("active_accepting_orders", "active_open", "active_paused")
SYSTEM_RULE_CODE_PREFIX = "SYSTEM"

# Confidence calculation constants
CONFIDENCE_PENALTY_NO_CATEGORY = 0.35
CONFIDENCE_PENALTY_GREY_BUCKET = 0.10
CONFIDENCE_PENALTY_BLACK_BUCKET = 0.20
CONFIDENCE_PENALTY_CATEGORY_CONFLICT = 0.20
CONFIDENCE_PENALTY_BUCKET_CONFLICT = 0.10
CONFIDENCE_PENALTY_PER_CONFLICT = 0.05
CONFIDENCE_PENALTY_MAX_CONFLICTS = 0.20


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _strip_text_punctuation(value: str) -> str:
    return re.sub(r"[^\w\s]+", " ", value)


def _normalize_text(value: str, *, case_sensitive: bool, strip_punctuation: bool) -> str:
    normalized = value
    if strip_punctuation:
        normalized = _strip_text_punctuation(normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not case_sensitive:
        normalized = normalized.lower()
    return normalized


def _clamp_confidence(value: float | int | None, default: float = 0.5) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def _keyword_list(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("keywords") or payload.get("values") or payload.get("terms") or []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _related_tags_text(value: Any) -> str:
    if value is None:
        return ""
    parts: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                for key in ("label", "slug", "name"):
                    if item.get(key):
                        parts.append(str(item[key]))
            else:
                parts.append(str(item))
    elif isinstance(value, dict):
        for key in ("label", "slug", "name"):
            if value.get(key):
                parts.append(str(value[key]))
    else:
        parts.append(str(value))
    return " ".join(parts)


def _build_source_fingerprint(market: Market) -> str:
    payload = {
        "market_id": market.market_id,
        "question": market.question,
        "description": market.description,
        "resolution_criteria": market.resolution_criteria,
        "category_raw": market.category_raw,
        "related_tags": market.related_tags,
        "market_status": market.market_status,
        "close_time": _ensure_utc_datetime(market.close_time).isoformat() if market.close_time else None,
        "source_updated_at": (
            _ensure_utc_datetime(market.source_updated_at).isoformat() if market.source_updated_at else None
        ),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _system_explanation(
    *,
    rule_code: str,
    rule_name: str,
    action_type: str,
    explanation_type: str,
    target_tag_code: str | None = None,
    confidence_delta: float | None = None,
    explanation_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "rule_code": rule_code,
        "rule_name": rule_name,
        "action_type": action_type,
        "target_tag_code": target_tag_code,
        "explanation_type": explanation_type,
        "confidence_delta": confidence_delta,
        "explanation_payload": explanation_payload or {},
    }


class MarketAutoClassificationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _build_market_texts(
        self,
        market: Market,
        *,
        case_sensitive: bool,
        strip_punctuation: bool,
    ) -> tuple[dict[str, str], dict[str, str]]:
        raw_texts = {
            "question": _clean_text(market.question),
            "description": _clean_text(market.description),
            "resolution_criteria": _clean_text(market.resolution_criteria),
            "category_raw": _clean_text(market.category_raw),
            "related_tags": _clean_text(_related_tags_text(market.related_tags)),
        }
        normalized_texts = {
            key: _normalize_text(value, case_sensitive=case_sensitive, strip_punctuation=strip_punctuation)
            for key, value in raw_texts.items()
        }
        return raw_texts, normalized_texts

    @staticmethod
    def _load_active_rule_version(session) -> TagRuleVersion:
        version = session.scalar(
            select(TagRuleVersion)
            .options(selectinload(TagRuleVersion.rules))
            .where(TagRuleVersion.status == ACTIVE_TAGGING_VERSION_STATUS)
            .order_by(TagRuleVersion.activated_at.desc(), TagRuleVersion.created_at.desc())
        )
        if version is None:
            raise ValueError("未找到 active 状态的 tagging 规则版本。")
        return version

    @staticmethod
    def _match_rule(
        *,
        rule,
        raw_texts: dict[str, str],
        normalized_texts: dict[str, str],
        case_sensitive: bool,
        strip_punctuation: bool,
    ) -> tuple[bool, dict[str, Any]]:
        scopes = [scope for scope in rule.match_scope if scope in normalized_texts]
        if not scopes:
            return False, {"scopes": [], "matched_terms": []}

        normalized_scope_values = [normalized_texts[scope] for scope in scopes if normalized_texts[scope]]
        raw_scope_values = [raw_texts[scope] for scope in scopes if raw_texts[scope]]
        normalized_combined = " ".join(normalized_scope_values).strip()
        raw_combined = " ".join(raw_scope_values).strip()
        if not normalized_combined and not raw_combined:
            return False, {"scopes": scopes, "matched_terms": []}

        matched_terms: list[str] = []
        operator = rule.match_operator
        payload = rule.match_payload or {}

        if operator in {"contains_any", "contains_all", "exact", "equals_any"}:
            keywords = [
                _normalize_text(keyword, case_sensitive=case_sensitive, strip_punctuation=strip_punctuation)
                for keyword in _keyword_list(payload)
            ]
            keywords = [keyword for keyword in keywords if keyword]
            if not keywords:
                return False, {"scopes": scopes, "matched_terms": []}

            if operator == "contains_any":
                matched_terms = [keyword for keyword in keywords if keyword in normalized_combined]
                return bool(matched_terms), {"scopes": scopes, "matched_terms": matched_terms}

            if operator == "contains_all":
                matched_terms = [keyword for keyword in keywords if keyword in normalized_combined]
                return len(matched_terms) == len(keywords), {"scopes": scopes, "matched_terms": matched_terms}

            if operator == "exact":
                for keyword in keywords:
                    if normalized_combined == keyword:
                        matched_terms = [keyword]
                        return True, {"scopes": scopes, "matched_terms": matched_terms}
                return False, {"scopes": scopes, "matched_terms": []}

            for keyword in keywords:
                if keyword in normalized_scope_values:
                    matched_terms.append(keyword)
            return bool(matched_terms), {"scopes": scopes, "matched_terms": matched_terms}

        if operator == "regex":
            patterns = payload.get("patterns") or []
            if not patterns and payload.get("pattern"):
                patterns = [payload["pattern"]]
            flags = 0 if case_sensitive else re.IGNORECASE
            for pattern in patterns:
                regex = re.compile(str(pattern), flags=flags)
                hit = regex.search(raw_combined if case_sensitive else raw_combined.lower())
                if hit is not None:
                    matched_terms.append(hit.group(0))
            return bool(matched_terms), {"scopes": scopes, "matched_terms": matched_terms}

        return False, {"scopes": scopes, "matched_terms": []}

    def classify_markets(
        self,
        *,
        classified_at: datetime,
        market_limit: int | None = None,
    ) -> dict[str, Any]:
        effective_market_limit = market_limit
        if effective_market_limit is None or effective_market_limit <= 0:
            effective_market_limit = self._settings.tagging_market_limit
            if effective_market_limit <= 0:
                effective_market_limit = None

        stats: dict[str, Any] = {
            "classified_at": classified_at.isoformat(),
            "selected_markets": 0,
            "created": 0,
            "skipped_existing": 0,
            "Tagged": 0,
            "ReviewRequired": 0,
            "Blocked": 0,
            "ClassificationFailed": 0,
            "review_tasks_created": 0,
            "sample_results": [],
        }

        with session_scope() as session:
            active_version = self._load_active_rule_version(session)
            stmt = (
                select(Market)
                .where(Market.market_status.in_(CLASSIFIABLE_MARKET_STATUSES))
                .order_by(Market.source_updated_at.desc(), Market.updated_at.desc())
            )
            if effective_market_limit:
                stmt = stmt.limit(effective_market_limit)

            markets = session.scalars(stmt).all()
            stats["selected_markets"] = len(markets)

            fingerprints_by_market_id = {
                market.id: _build_source_fingerprint(market) for market in markets
            }
            existing_results = set(
                session.execute(
                    select(
                        MarketClassificationResult.market_ref_id,
                        MarketClassificationResult.source_fingerprint,
                    ).where(
                        MarketClassificationResult.rule_version == active_version.version_code,
                        MarketClassificationResult.market_ref_id.in_(list(fingerprints_by_market_id.keys())),
                    )
                ).all()
            ) if fingerprints_by_market_id else set()

            dictionary_snapshot = deepcopy(active_version.dictionary_snapshot)
            dictionary_by_code = {
                item["tag_code"]: item for item in dictionary_snapshot if isinstance(item, dict) and item.get("tag_code")
            }

            for market in markets:
                fingerprint = fingerprints_by_market_id[market.id]
                if (market.id, fingerprint) in existing_results:
                    stats["skipped_existing"] += 1
                    continue

                outcome = self._classify_market(
                    market=market,
                    active_version=active_version,
                    dictionary_by_code=dictionary_by_code,
                )
                try:
                    with session.begin_nested():
                        result = MarketClassificationResult(
                            market_ref_id=market.id,
                            rule_version=active_version.version_code,
                            source_fingerprint=fingerprint,
                            classification_status=outcome["classification_status"],
                            primary_category_code=outcome["primary_category_code"],
                            admission_bucket_code=outcome["admission_bucket_code"],
                            confidence=outcome["confidence"],
                            requires_review=outcome["requires_review"],
                            conflict_count=outcome["conflict_count"],
                            failure_reason_code=outcome["failure_reason_code"],
                            result_details=outcome["result_details"],
                            classified_at=classified_at,
                        )
                        session.add(result)
                        session.flush()

                        for assignment in outcome["assignments"]:
                            session.add(
                                MarketTagAssignment(
                                    classification_result_id=result.id,
                                    market_ref_id=market.id,
                                    tag_code=assignment["tag_code"],
                                    tag_type=assignment["tag_type"],
                                    assignment_role=assignment["assignment_role"],
                                    confidence=assignment["confidence"],
                                    assignment_metadata=assignment["assignment_metadata"],
                                )
                            )

                        for explanation in outcome["explanations"]:
                            session.add(
                                MarketTagExplanation(
                                    classification_result_id=result.id,
                                    market_ref_id=market.id,
                                    rule_code=explanation["rule_code"],
                                    rule_name=explanation["rule_name"],
                                    action_type=explanation["action_type"],
                                    target_tag_code=explanation["target_tag_code"],
                                    explanation_type=explanation["explanation_type"],
                                    confidence_delta=explanation["confidence_delta"],
                                    explanation_payload=explanation["explanation_payload"],
                                )
                            )

                        if outcome["review_task"] is not None:
                            session.add(
                                MarketReviewTask(
                                    market_ref_id=market.id,
                                    classification_result_id=result.id,
                                    queue_status="open",
                                    review_reason_code=outcome["review_task"]["review_reason_code"],
                                    priority=outcome["review_task"]["priority"],
                                    review_payload=outcome["review_task"]["review_payload"],
                                )
                            )
                            stats["review_tasks_created"] += 1
                except IntegrityError:
                    stats["skipped_existing"] += 1
                    continue

                existing_results.add((market.id, fingerprint))
                stats["created"] += 1
                stats[outcome["classification_status"]] += 1
                if len(stats["sample_results"]) < 10:
                    stats["sample_results"].append(
                        {
                            "market_id": market.market_id,
                            "classification_status": outcome["classification_status"],
                            "primary_category_code": outcome["primary_category_code"],
                            "admission_bucket_code": outcome["admission_bucket_code"],
                            "failure_reason_code": outcome["failure_reason_code"],
                        }
                    )

        return stats

    def _classify_market(
        self,
        *,
        market: Market,
        active_version: TagRuleVersion,
        dictionary_by_code: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        config_payload = deepcopy(active_version.config_payload or {})
        matching_config = config_payload.get("matching", {})
        review_config = config_payload.get("review", {})
        admission_config = config_payload.get("admission", {})

        case_sensitive = bool(matching_config.get("case_sensitive", False))
        strip_punctuation = bool(matching_config.get("strip_punctuation", True))
        low_confidence_threshold = float(review_config.get("low_confidence_threshold", 0.65))
        conflict_requires_review = bool(review_config.get("conflict_requires_review", True))

        raw_texts, normalized_texts = self._build_market_texts(
            market,
            case_sensitive=case_sensitive,
            strip_punctuation=strip_punctuation,
        )

        category_candidates: dict[str, dict[str, Any]] = {}
        factor_candidates: dict[str, dict[str, Any]] = {}
        bucket_candidates: dict[str, dict[str, Any]] = {}
        review_reasons: list[str] = []
        matched_rule_codes: list[str] = []
        explanations: list[dict[str, Any]] = []

        for rule in sorted(active_version.rules, key=lambda item: (item.priority, item.rule_code)):
            if not rule.enabled:
                continue

            matched, match_details = self._match_rule(
                rule=rule,
                raw_texts=raw_texts,
                normalized_texts=normalized_texts,
                case_sensitive=case_sensitive,
                strip_punctuation=strip_punctuation,
            )
            if not matched:
                continue

            matched_rule_codes.append(rule.rule_code)
            confidence_value = _clamp_confidence(rule.effect_payload.get("confidence"), default=0.5)
            explanations.append(
                {
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "action_type": rule.action_type,
                    "target_tag_code": rule.target_tag_code,
                    "explanation_type": "rule_match",
                    "confidence_delta": confidence_value,
                    "explanation_payload": {
                        "match_scope": match_details["scopes"],
                        "matched_terms": match_details["matched_terms"],
                        "match_operator": rule.match_operator,
                        "match_payload": deepcopy(rule.match_payload),
                        "effect_payload": deepcopy(rule.effect_payload),
                    },
                }
            )

            target_code = rule.target_tag_code
            target_meta = dictionary_by_code.get(target_code, {}) if target_code else {}

            if rule.action_type == "assign_primary_category" and target_code:
                self._register_candidate(
                    category_candidates,
                    tag_code=target_code,
                    confidence=confidence_value,
                    rule_code=rule.rule_code,
                    rule_name=rule.rule_name,
                    tag_type=target_meta.get("tag_type", "category"),
                )
            elif rule.action_type == "add_risk_factor" and target_code:
                self._register_candidate(
                    factor_candidates,
                    tag_code=target_code,
                    confidence=confidence_value,
                    rule_code=rule.rule_code,
                    rule_name=rule.rule_name,
                    tag_type=target_meta.get("tag_type", "risk_factor"),
                )
            elif rule.action_type == "set_admission_bucket" and target_code:
                self._register_candidate(
                    bucket_candidates,
                    tag_code=target_code,
                    confidence=confidence_value,
                    rule_code=rule.rule_code,
                    rule_name=rule.rule_name,
                    tag_type=target_meta.get("tag_type", "list_bucket"),
                )
            elif rule.action_type == "require_review":
                review_reasons.append("TAG_EXPLICIT_REVIEW")

        selected_category_code = self._pick_highest_confidence_tag(category_candidates)
        selected_bucket_code = self._pick_bucket_tag(bucket_candidates, dictionary_by_code)
        factor_codes = sorted(factor_candidates.keys())
        conflict_count = 0
        failure_reason_code = None
        requires_review = False

        if not selected_category_code:
            failure_reason_code = "TAG_NO_CATEGORY_MATCH"
            requires_review = True
            explanations.append(
                _system_explanation(
                    rule_code=f"{SYSTEM_RULE_CODE_PREFIX}_NO_CATEGORY_MATCH",
                    rule_name="未命中一级类别规则",
                    action_type="require_review",
                    explanation_type="review_decision",
                    explanation_payload={"reason_code": failure_reason_code},
                )
            )
        elif len(category_candidates) > 1:
            conflict_count += len(category_candidates) - 1
            if conflict_requires_review:
                requires_review = True
                failure_reason_code = failure_reason_code or "TAG_CATEGORY_CONFLICT"
            explanations.append(
                _system_explanation(
                    rule_code=f"{SYSTEM_RULE_CODE_PREFIX}_CATEGORY_CONFLICT",
                    rule_name="一级类别冲突",
                    action_type="require_review",
                    explanation_type="conflict",
                    explanation_payload={"candidate_codes": sorted(category_candidates.keys())},
                )
            )

        if not selected_bucket_code:
            selected_bucket_code = admission_config.get("grey_bucket_code", "LIST_GREY")
            requires_review = True
            failure_reason_code = failure_reason_code or "TAG_NO_BUCKET_MATCH"
            explanations.append(
                _system_explanation(
                    rule_code=f"{SYSTEM_RULE_CODE_PREFIX}_DEFAULT_GREY_BUCKET",
                    rule_name="未命中准入桶规则，默认灰名单",
                    action_type="set_admission_bucket",
                    explanation_type="default_bucket",
                    target_tag_code=selected_bucket_code,
                    explanation_payload={"reason_code": "TAG_NO_BUCKET_MATCH"},
                )
            )
        elif len(bucket_candidates) > 1:
            conflict_count += len(bucket_candidates) - 1
            requires_review = True
            failure_reason_code = failure_reason_code or "TAG_BUCKET_CONFLICT"
            explanations.append(
                _system_explanation(
                    rule_code=f"{SYSTEM_RULE_CODE_PREFIX}_BUCKET_CONFLICT",
                    rule_name="准入桶冲突",
                    action_type="require_review",
                    explanation_type="conflict",
                    explanation_payload={"candidate_codes": sorted(bucket_candidates.keys())},
                )
            )

        if review_reasons:
            requires_review = True
            failure_reason_code = failure_reason_code or review_reasons[0]

        confidence = self._calculate_confidence(
            selected_category_code=selected_category_code,
            selected_bucket_code=selected_bucket_code,
            category_candidates=category_candidates,
            bucket_candidates=bucket_candidates,
            low_confidence_threshold=low_confidence_threshold,
            requires_review=requires_review,
            conflict_count=conflict_count,
        )

        if confidence < low_confidence_threshold:
            requires_review = True
            failure_reason_code = failure_reason_code or "TAG_LOW_CONFIDENCE"
            explanations.append(
                _system_explanation(
                    rule_code=f"{SYSTEM_RULE_CODE_PREFIX}_LOW_CONFIDENCE",
                    rule_name="分类置信度低于阈值",
                    action_type="require_review",
                    explanation_type="review_decision",
                    confidence_delta=confidence,
                    explanation_payload={
                        "confidence": confidence,
                        "threshold": low_confidence_threshold,
                    },
                )
            )

        classification_status = "Tagged"
        if selected_bucket_code == admission_config.get("black_bucket_code", "LIST_BLACK"):
            classification_status = "Blocked"
            requires_review = True
            failure_reason_code = failure_reason_code or "TAG_BLACKLIST_MATCH"
        elif requires_review:
            classification_status = "ReviewRequired"

        assignments = self._build_assignments(
            market=market,
            selected_category_code=selected_category_code,
            selected_bucket_code=selected_bucket_code,
            factor_codes=factor_codes,
            confidence=confidence,
            category_candidates=category_candidates,
            factor_candidates=factor_candidates,
            bucket_candidates=bucket_candidates,
            dictionary_by_code=dictionary_by_code,
        )

        review_task = None
        if classification_status in {"ReviewRequired", "Blocked"}:
            review_task = {
                "review_reason_code": failure_reason_code or "TAG_MANUAL_REVIEW",
                "priority": "high" if classification_status == "Blocked" or conflict_count > 0 else "normal",
                "review_payload": {
                    "classification_status": classification_status,
                    "primary_category_code": selected_category_code,
                    "admission_bucket_code": selected_bucket_code,
                    "confidence": confidence,
                    "matched_rule_codes": matched_rule_codes,
                    "failure_reason_code": failure_reason_code,
                },
            }

        return {
            "classification_status": classification_status,
            "primary_category_code": selected_category_code,
            "admission_bucket_code": selected_bucket_code,
            "confidence": confidence,
            "requires_review": requires_review,
            "conflict_count": conflict_count,
            "failure_reason_code": failure_reason_code,
            "assignments": assignments,
            "explanations": explanations,
            "review_task": review_task,
            "result_details": {
                "summary": {
                    "classification_status": classification_status,
                    "requires_review": requires_review,
                    "primary_category_code": selected_category_code,
                    "admission_bucket_code": selected_bucket_code,
                    "risk_factor_codes": factor_codes,
                    "confidence": confidence,
                    "conflict_count": conflict_count,
                    "failure_reason_code": failure_reason_code,
                },
                "matched_rule_codes": matched_rule_codes,
                "category_candidates": deepcopy(category_candidates),
                "factor_candidates": deepcopy(factor_candidates),
                "bucket_candidates": deepcopy(bucket_candidates),
                "normalized_fields": normalized_texts,
            },
        }

    @staticmethod
    def _register_candidate(
        store: dict[str, dict[str, Any]],
        *,
        tag_code: str,
        confidence: float,
        rule_code: str,
        rule_name: str,
        tag_type: str,
    ) -> None:
        candidate = store.get(tag_code)
        if candidate is None:
            store[tag_code] = {
                "tag_code": tag_code,
                "tag_type": tag_type,
                "confidence": confidence,
                "rule_codes": [rule_code],
                "rule_names": [rule_name],
            }
            return

        candidate["confidence"] = max(candidate["confidence"], confidence)
        if rule_code not in candidate["rule_codes"]:
            candidate["rule_codes"].append(rule_code)
        if rule_name not in candidate["rule_names"]:
            candidate["rule_names"].append(rule_name)

    @staticmethod
    def _pick_highest_confidence_tag(candidates: dict[str, dict[str, Any]]) -> str | None:
        if not candidates:
            return None
        ordered = sorted(
            candidates.values(),
            key=lambda item: (-float(item["confidence"]), item["tag_code"]),
        )
        return ordered[0]["tag_code"]

    @staticmethod
    def _pick_bucket_tag(
        candidates: dict[str, dict[str, Any]],
        dictionary_by_code: dict[str, dict[str, Any]],
    ) -> str | None:
        if not candidates:
            return None

        def bucket_sort_key(item: dict[str, Any]) -> tuple[int, float, str]:
            metadata = dictionary_by_code.get(item["tag_code"], {}).get("tag_metadata", {}) or {}
            rank = int(metadata.get("rank", 0))
            return (-rank, -float(item["confidence"]), item["tag_code"])

        ordered = sorted(candidates.values(), key=bucket_sort_key)
        return ordered[0]["tag_code"]

    @staticmethod
    def _calculate_confidence(
        *,
        selected_category_code: str | None,
        selected_bucket_code: str | None,
        category_candidates: dict[str, dict[str, Any]],
        bucket_candidates: dict[str, dict[str, Any]],
        low_confidence_threshold: float,
        requires_review: bool,
        conflict_count: int,
    ) -> float:
        confidence = 0.0
        if selected_category_code and selected_category_code in category_candidates:
            confidence = float(category_candidates[selected_category_code]["confidence"])

        # Apply penalties using constants
        if not selected_category_code:
            confidence -= CONFIDENCE_PENALTY_NO_CATEGORY
        if selected_bucket_code == "LIST_GREY":
            confidence -= CONFIDENCE_PENALTY_GREY_BUCKET
        if selected_bucket_code == "LIST_BLACK":
            confidence -= CONFIDENCE_PENALTY_BLACK_BUCKET
        if len(category_candidates) > 1:
            confidence -= CONFIDENCE_PENALTY_CATEGORY_CONFLICT
        if len(bucket_candidates) > 1:
            confidence -= CONFIDENCE_PENALTY_BUCKET_CONFLICT
        if requires_review:
            confidence = min(confidence, low_confidence_threshold - 0.05)

        # Apply conflict penalty with cap
        conflict_penalty = min(CONFIDENCE_PENALTY_MAX_CONFLICTS, conflict_count * CONFIDENCE_PENALTY_PER_CONFLICT)
        confidence -= conflict_penalty

        return _clamp_confidence(confidence, default=0.0)

    @staticmethod
    def _build_assignments(
        *,
        market: Market,
        selected_category_code: str | None,
        selected_bucket_code: str | None,
        factor_codes: list[str],
        confidence: float,
        category_candidates: dict[str, dict[str, Any]],
        factor_candidates: dict[str, dict[str, Any]],
        bucket_candidates: dict[str, dict[str, Any]],
        dictionary_by_code: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        assignments: list[dict[str, Any]] = []

        if selected_category_code is not None:
            category_meta = dictionary_by_code.get(selected_category_code, {})
            assignments.append(
                {
                    "tag_code": selected_category_code,
                    "tag_type": category_meta.get("tag_type", "category"),
                    "assignment_role": "primary_category",
                    "confidence": confidence,
                    "assignment_metadata": deepcopy(category_candidates.get(selected_category_code, {})),
                }
            )

        for factor_code in factor_codes:
            factor_meta = dictionary_by_code.get(factor_code, {})
            assignments.append(
                {
                    "tag_code": factor_code,
                    "tag_type": factor_meta.get("tag_type", "risk_factor"),
                    "assignment_role": "risk_factor",
                    "confidence": float(factor_candidates[factor_code]["confidence"]),
                    "assignment_metadata": deepcopy(factor_candidates[factor_code]),
                }
            )

        if selected_bucket_code is not None:
            bucket_meta = dictionary_by_code.get(selected_bucket_code, {})
            assignments.append(
                {
                    "tag_code": selected_bucket_code,
                    "tag_type": bucket_meta.get("tag_type", "list_bucket"),
                    "assignment_role": "admission_bucket",
                    "confidence": float(bucket_candidates.get(selected_bucket_code, {}).get("confidence", confidence)),
                    "assignment_metadata": deepcopy(bucket_candidates.get(selected_bucket_code, {})),
                }
            )

        return assignments


@lru_cache
def get_market_auto_classification_service() -> MarketAutoClassificationService:
    return MarketAutoClassificationService(settings=get_settings())
