from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.models import TagDictionaryEntry, TagRule, TagRuleVersion
from db.session import session_scope
from services.audit import AuditEvent, get_audit_log_service
from services.tagging.contracts import TagDefinitionInput, TagRuleInput, TagRuleVersionCreateInput


VALID_TAG_TYPES = {"category", "risk_factor", "list_bucket"}
VALID_RULE_KINDS = {"keyword", "regex", "structured_match", "manual_seed"}
VALID_ACTION_TYPES = {
    "assign_primary_category",
    "add_risk_factor",
    "set_admission_bucket",
    "require_review",
    "attach_note",
}
VALID_MATCH_OPERATORS = {"contains_any", "contains_all", "exact", "equals_any", "regex"}
ACTIVE_VERSION_STATUS = "active"
DRAFT_VERSION_STATUS = "draft"

DEFAULT_TAGGING_CONFIG: dict[str, Any] = {
    "matching": {
        "text_fields": [
            "question",
            "description",
            "resolution_criteria",
            "category_raw",
            "related_tags",
        ],
        "case_sensitive": False,
        "strip_punctuation": True,
    },
    "classification": {
        "primary_category_limit": 1,
        "conflict_policy": "review_required",
        "allow_multi_factor": True,
    },
    "review": {
        "low_confidence_threshold": 0.65,
        "conflict_requires_review": True,
        "empty_match_requires_review": True,
    },
    "admission": {
        "white_bucket_code": "LIST_WHITE",
        "grey_bucket_code": "LIST_GREY",
        "black_bucket_code": "LIST_BLACK",
    },
}

DEFAULT_TAG_DEFINITIONS: list[TagDefinitionInput] = [
    TagDefinitionInput(
        tag_code="CAT_NUMERIC",
        tag_name="Numeric",
        tag_type="category",
        dimension="primary_category",
        description="以数值阈值、计数或区间作为核心结算标准的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=10,
    ),
    TagDefinitionInput(
        tag_code="CAT_TIME",
        tag_name="Time",
        tag_type="category",
        dimension="primary_category",
        description="以具体时间点、日期窗口或时序事件为主的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=20,
    ),
    TagDefinitionInput(
        tag_code="CAT_STATISTICAL",
        tag_name="Statistical",
        tag_type="category",
        dimension="primary_category",
        description="以统计结果、样本聚合或概率型结算为主的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=30,
    ),
    TagDefinitionInput(
        tag_code="CAT_PERSON",
        tag_name="Person",
        tag_type="category",
        dimension="primary_category",
        description="围绕具体个人行为、状态、任命或言论展开的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=40,
    ),
    TagDefinitionInput(
        tag_code="CAT_MACRO",
        tag_name="Macro",
        tag_type="category",
        dimension="primary_category",
        description="与宏观经济、政策、央行、通胀或总量变量相关的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=50,
    ),
    TagDefinitionInput(
        tag_code="CAT_GEOPOLITICAL",
        tag_name="GeoPolitical",
        tag_type="category",
        dimension="primary_category",
        description="与国际关系、战争、外交或地缘政治事件相关的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=60,
    ),
    TagDefinitionInput(
        tag_code="CAT_DISASTER",
        tag_name="Disaster",
        tag_type="category",
        dimension="primary_category",
        description="与自然灾害、事故或突发灾难事件相关的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=70,
    ),
    TagDefinitionInput(
        tag_code="CAT_SPORTS",
        tag_name="Sports",
        tag_type="category",
        dimension="primary_category",
        description="与体育赛事结果、表现或赛季事件相关的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=80,
    ),
    TagDefinitionInput(
        tag_code="CAT_CRYPTO_ASSET",
        tag_name="CryptoAsset",
        tag_type="category",
        dimension="primary_category",
        description="与加密资产价格、链上事件或协议状态相关的市场。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=90,
    ),
    TagDefinitionInput(
        tag_code="CAT_OTHER",
        tag_name="Other",
        tag_type="category",
        dimension="primary_category",
        description="暂未落入既有主类别的市场兜底标签。",
        tag_metadata={"exclusive_group": "primary_category"},
        sort_order=100,
    ),
    TagDefinitionInput(
        tag_code="RF_OBJECTIVE_RESOLUTION",
        tag_name="客观结算",
        tag_type="risk_factor",
        dimension="resolution_objectivity",
        description="结算标准是否清晰且能由明确客观事实验证。",
        tag_metadata={"polarity": "positive"},
        sort_order=200,
    ),
    TagDefinitionInput(
        tag_code="RF_SOURCE_AUTHORITY_CLEAR",
        tag_name="权威数据源清晰",
        tag_type="risk_factor",
        dimension="source_authority",
        description="市场是否依赖明确且可信的权威数据源。",
        tag_metadata={"polarity": "positive"},
        sort_order=210,
    ),
    TagDefinitionInput(
        tag_code="RF_SOURCE_COUNT_MULTIPLE",
        tag_name="多数据源交叉验证",
        tag_type="risk_factor",
        dimension="source_count",
        description="结算或判断是否可由多个独立来源交叉验证。",
        tag_metadata={"polarity": "positive"},
        sort_order=220,
    ),
    TagDefinitionInput(
        tag_code="RF_MANUAL_INTERPRETATION_REQUIRED",
        tag_name="依赖人工解释",
        tag_type="risk_factor",
        dimension="interpretation_dependency",
        description="市场判断需要人工主观解释、上下文裁量或语义推断。",
        tag_metadata={"polarity": "negative"},
        sort_order=230,
    ),
    TagDefinitionInput(
        tag_code="RF_SINGLE_EVENT_DEPENDENT",
        tag_name="依赖单一新闻事件",
        tag_type="risk_factor",
        dimension="single_event_dependency",
        description="市场走势高度依赖单一突发事件或单点消息。",
        tag_metadata={"polarity": "negative"},
        sort_order=240,
    ),
    TagDefinitionInput(
        tag_code="RF_SINGLE_ASSET_CORRELATED",
        tag_name="与单一资产强相关",
        tag_type="risk_factor",
        dimension="single_asset_dependency",
        description="市场结果与单一资产价格或状态高度耦合。",
        tag_metadata={"polarity": "contextual"},
        sort_order=250,
    ),
    TagDefinitionInput(
        tag_code="RF_MACRO_CORRELATED",
        tag_name="与宏观风险强相关",
        tag_type="risk_factor",
        dimension="macro_dependency",
        description="市场受宏观政策、流动性环境或系统性风险主导。",
        tag_metadata={"polarity": "contextual"},
        sort_order=260,
    ),
    TagDefinitionInput(
        tag_code="RF_DISPUTE_TEMPLATE_SIMILAR",
        tag_name="存在历史争议模板相似性",
        tag_type="risk_factor",
        dimension="dispute_template",
        description="市场在结构上接近历史高争议模板，需要提高审慎级别。",
        tag_metadata={"polarity": "negative"},
        sort_order=270,
    ),
    TagDefinitionInput(
        tag_code="RF_PRE_CLOSE_INFORMATION_JUMP",
        tag_name="到期前信息跳变风险",
        tag_type="risk_factor",
        dimension="pre_close_information_jump",
        description="市场在临近到期时可能出现显著信息更新或价格跳变。",
        tag_metadata={"polarity": "negative"},
        sort_order=280,
    ),
    TagDefinitionInput(
        tag_code="RF_LIQUIDITY_THIN",
        tag_name="流动性偏薄",
        tag_type="risk_factor",
        dimension="liquidity_tier",
        description="盘口深度不足或成交稀薄，可能导致研究可得但执行不可得。",
        tag_metadata={"polarity": "negative"},
        sort_order=290,
    ),
    TagDefinitionInput(
        tag_code="RF_THEME_CLUSTERED",
        tag_name="主题聚类集中",
        tag_type="risk_factor",
        dimension="theme_cluster",
        description="市场与其他市场在主题上高度重叠，容易形成风险簇暴露。",
        tag_metadata={"polarity": "contextual"},
        sort_order=300,
    ),
    TagDefinitionInput(
        tag_code="LIST_WHITE",
        tag_name="白名单",
        tag_type="list_bucket",
        dimension="admission_bucket",
        description="满足研究与潜在交易准入条件的市场桶。",
        tag_metadata={"rank": 1},
        sort_order=400,
    ),
    TagDefinitionInput(
        tag_code="LIST_GREY",
        tag_name="灰名单",
        tag_type="list_bucket",
        dimension="admission_bucket",
        description="可进入观察或人工审核，但默认不进入实盘流程的市场桶。",
        tag_metadata={"rank": 2},
        sort_order=410,
    ),
    TagDefinitionInput(
        tag_code="LIST_BLACK",
        tag_name="黑名单",
        tag_type="list_bucket",
        dimension="admission_bucket",
        description="应被直接排除或长期冻结研究资格的市场桶。",
        tag_metadata={"rank": 3},
        sort_order=420,
    ),
]


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_upper_code(value: str, *, field_name: str) -> str:
    normalized = value.strip().replace("-", "_").replace(" ", "_").upper()
    if not normalized:
        raise ValueError(f"{field_name} 不能为空。")
    if len(normalized) > 64:
        raise ValueError(f"{field_name} 长度不能超过 64。")
    return normalized


def _normalize_version_code(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("version_code 不能为空。")
    if len(normalized) > 64:
        raise ValueError("version_code 长度不能超过 64。")
    return normalized


def _normalize_aliases(values: list[str] | None) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        cleaned = raw.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        aliases.append(cleaned)
    return aliases


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _normalize_tag_definition_payload(definition: TagDefinitionInput) -> dict[str, Any]:
    tag_type = definition.tag_type.strip().lower()
    if tag_type not in VALID_TAG_TYPES:
        raise ValueError(f"不支持的 tag_type: {definition.tag_type}")

    dimension = definition.dimension.strip().lower()
    if not dimension:
        raise ValueError("dimension 不能为空。")

    tag_name = definition.tag_name.strip()
    if not tag_name:
        raise ValueError("tag_name 不能为空。")

    if definition.sort_order < 0:
        raise ValueError("sort_order 不能小于 0。")

    tag_metadata = deepcopy(definition.tag_metadata or {})
    if not isinstance(tag_metadata, dict):
        raise ValueError("tag_metadata 必须为对象。")

    return {
        "tag_code": _normalize_upper_code(definition.tag_code, field_name="tag_code"),
        "tag_name": tag_name,
        "tag_type": tag_type,
        "dimension": dimension,
        "description": _clean_text(definition.description),
        "aliases": _normalize_aliases(definition.aliases),
        "tag_metadata": tag_metadata,
        "sort_order": definition.sort_order,
        "is_active": bool(definition.is_active),
    }


def _normalize_rule_payload(rule: TagRuleInput, *, allowed_tag_codes: set[str]) -> dict[str, Any]:
    rule_kind = rule.rule_kind.strip().lower()
    if rule_kind not in VALID_RULE_KINDS:
        raise ValueError(f"不支持的 rule_kind: {rule.rule_kind}")

    action_type = rule.action_type.strip().lower()
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(f"不支持的 action_type: {rule.action_type}")

    match_operator = rule.match_operator.strip().lower()
    if match_operator not in VALID_MATCH_OPERATORS:
        raise ValueError(f"不支持的 match_operator: {rule.match_operator}")

    match_scope = [value.strip() for value in rule.match_scope if value.strip()]
    if not match_scope:
        raise ValueError(f"规则 {rule.rule_code} 至少需要一个 match_scope。")

    if rule.priority < 0:
        raise ValueError(f"规则 {rule.rule_code} 的 priority 不能小于 0。")

    target_tag_code = None
    if rule.target_tag_code is not None:
        target_tag_code = _normalize_upper_code(rule.target_tag_code, field_name="target_tag_code")
        if target_tag_code not in allowed_tag_codes:
            raise ValueError(f"规则 {rule.rule_code} 引用了未定义标签 {target_tag_code}。")

    if action_type in {"assign_primary_category", "add_risk_factor", "set_admission_bucket"} and target_tag_code is None:
        raise ValueError(f"规则 {rule.rule_code} 的 action_type={action_type} 必须指定 target_tag_code。")

    match_payload = deepcopy(rule.match_payload or {})
    effect_payload = deepcopy(rule.effect_payload or {})
    if not isinstance(match_payload, dict):
        raise ValueError(f"规则 {rule.rule_code} 的 match_payload 必须为对象。")
    if not isinstance(effect_payload, dict):
        raise ValueError(f"规则 {rule.rule_code} 的 effect_payload 必须为对象。")

    return {
        "rule_code": _normalize_upper_code(rule.rule_code, field_name="rule_code"),
        "rule_name": rule.rule_name.strip(),
        "rule_kind": rule_kind,
        "action_type": action_type,
        "target_tag_code": target_tag_code,
        "priority": rule.priority,
        "enabled": bool(rule.enabled),
        "match_scope": match_scope,
        "match_operator": match_operator,
        "match_payload": match_payload,
        "effect_payload": effect_payload,
        "notes": _clean_text(rule.notes),
    }


def _serialize_tag_definition(entry: TagDictionaryEntry) -> dict[str, Any]:
    return {
        "tag_code": entry.tag_code,
        "tag_name": entry.tag_name,
        "tag_type": entry.tag_type,
        "dimension": entry.dimension,
        "description": entry.description,
        "aliases": deepcopy(entry.aliases or []),
        "tag_metadata": deepcopy(entry.tag_metadata or {}),
        "sort_order": entry.sort_order,
        "is_active": entry.is_active,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def _serialize_rule(rule: TagRule) -> dict[str, Any]:
    return {
        "rule_code": rule.rule_code,
        "rule_name": rule.rule_name,
        "rule_kind": rule.rule_kind,
        "action_type": rule.action_type,
        "target_tag_code": rule.target_tag_code,
        "priority": rule.priority,
        "enabled": rule.enabled,
        "match_scope": deepcopy(rule.match_scope),
        "match_operator": rule.match_operator,
        "match_payload": deepcopy(rule.match_payload),
        "effect_payload": deepcopy(rule.effect_payload),
        "notes": rule.notes,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
    }


def _compute_checksum(
    *,
    dictionary_snapshot: list[dict[str, Any]],
    config_payload: dict[str, Any],
    rules: list[dict[str, Any]],
) -> str:
    canonical_payload = json.dumps(
        {
            "dictionary_snapshot": dictionary_snapshot,
            "config_payload": config_payload,
            "rules": rules,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


class TaggingRuleService:
    def __init__(self) -> None:
        self._audit_service = get_audit_log_service()

    def list_tag_definitions(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        with session_scope() as session:
            stmt = (
                select(TagDictionaryEntry)
                .order_by(
                    TagDictionaryEntry.tag_type.asc(),
                    TagDictionaryEntry.dimension.asc(),
                    TagDictionaryEntry.sort_order.asc(),
                    TagDictionaryEntry.tag_code.asc(),
                )
            )
            if not include_inactive:
                stmt = stmt.where(TagDictionaryEntry.is_active.is_(True))
            entries = session.scalars(stmt).all()
            return [_serialize_tag_definition(entry) for entry in entries]

    def seed_default_dictionary(
        self,
        *,
        actor_id: str | None = None,
        actor_type: str | None = "system",
        request_id: str | None = None,
    ) -> dict[str, Any]:
        created = 0
        updated = 0
        tag_codes: list[str] = []

        with session_scope() as session:
            existing_map = {
                entry.tag_code: entry
                for entry in session.scalars(select(TagDictionaryEntry)).all()
            }

            for definition in DEFAULT_TAG_DEFINITIONS:
                payload = _normalize_tag_definition_payload(definition)
                entry = existing_map.get(payload["tag_code"])
                if entry is None:
                    session.add(TagDictionaryEntry(**payload))
                    created += 1
                else:
                    entry.tag_name = payload["tag_name"]
                    entry.tag_type = payload["tag_type"]
                    entry.dimension = payload["dimension"]
                    entry.description = payload["description"]
                    entry.aliases = payload["aliases"]
                    entry.tag_metadata = payload["tag_metadata"]
                    entry.sort_order = payload["sort_order"]
                    entry.is_active = payload["is_active"]
                    updated += 1
                tag_codes.append(payload["tag_code"])

        result = {
            "created": created,
            "updated": updated,
            "total": len(tag_codes),
            "tag_codes": tag_codes,
        }
        self._audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                object_type="tag_dictionary_catalog",
                object_id="default_seed_v1",
                action="seed",
                result="success",
                request_id=request_id,
                event_payload=result,
            )
        )
        return result

    def upsert_tag_definition(
        self,
        definition: TagDefinitionInput,
        *,
        actor_id: str | None = None,
        actor_type: str | None = "user",
        request_id: str | None = None,
    ) -> dict[str, Any]:
        payload = _normalize_tag_definition_payload(definition)

        with session_scope() as session:
            entry = session.scalar(
                select(TagDictionaryEntry).where(TagDictionaryEntry.tag_code == payload["tag_code"])
            )
            action = "create" if entry is None else "update"

            if entry is None:
                entry = TagDictionaryEntry(**payload)
                session.add(entry)
            else:
                entry.tag_name = payload["tag_name"]
                entry.tag_type = payload["tag_type"]
                entry.dimension = payload["dimension"]
                entry.description = payload["description"]
                entry.aliases = payload["aliases"]
                entry.tag_metadata = payload["tag_metadata"]
                entry.sort_order = payload["sort_order"]
                entry.is_active = payload["is_active"]

            session.flush()
            result = _serialize_tag_definition(entry)

        self._audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                object_type="tag_dictionary_entry",
                object_id=payload["tag_code"],
                action=action,
                result="success",
                request_id=request_id,
                event_payload=result,
            )
        )
        return result

    def create_rule_version(
        self,
        draft: TagRuleVersionCreateInput,
        *,
        actor_id: str | None = None,
        actor_type: str | None = "user",
        request_id: str | None = None,
        auto_activate: bool = False,
    ) -> dict[str, Any]:
        version_code = _normalize_version_code(draft.version_code)
        change_reason = _clean_text(draft.change_reason)
        if change_reason is None:
            raise ValueError("change_reason 不能为空。")

        config_payload = _merge_dict(DEFAULT_TAGGING_CONFIG, draft.config_payload or {})
        now = _now_utc()

        with session_scope() as session:
            existing = session.scalar(
                select(TagRuleVersion.id).where(TagRuleVersion.version_code == version_code)
            )
            if existing is not None:
                raise ValueError(f"version_code {version_code} 已存在。")

            base_version_id = None
            if draft.base_version_code is not None:
                base_version = session.scalar(
                    select(TagRuleVersion).where(
                        TagRuleVersion.version_code == _normalize_version_code(draft.base_version_code)
                    )
                )
                if base_version is None:
                    raise ValueError(f"base_version_code {draft.base_version_code} 不存在。")
                base_version_id = base_version.id

            dictionary_snapshot = self._build_dictionary_snapshot(session)
            allowed_tag_codes = {item["tag_code"] for item in dictionary_snapshot}
            normalized_rules = [
                _normalize_rule_payload(rule, allowed_tag_codes=allowed_tag_codes) for rule in draft.rules
            ]
            checksum = _compute_checksum(
                dictionary_snapshot=dictionary_snapshot,
                config_payload=config_payload,
                rules=normalized_rules,
            )

            version = TagRuleVersion(
                version_code=version_code,
                status=ACTIVE_VERSION_STATUS if auto_activate else DRAFT_VERSION_STATUS,
                release_kind="standard",
                base_version_id=base_version_id,
                change_reason=change_reason,
                evidence_summary=_clean_text(draft.evidence_summary),
                impact_summary=_clean_text(draft.impact_summary),
                rollback_plan=_clean_text(draft.rollback_plan),
                version_notes=_clean_text(draft.version_notes),
                dictionary_snapshot=dictionary_snapshot,
                config_payload=config_payload,
                checksum=checksum,
                created_by=_clean_text(actor_id),
                activated_by=_clean_text(actor_id) if auto_activate else None,
                activated_at=now if auto_activate else None,
            )
            session.add(version)
            session.flush()

            if auto_activate:
                self._ensure_version_activatable(
                    dictionary_snapshot=dictionary_snapshot,
                    rules=normalized_rules,
                )
                superseded_version_id = self._retire_active_versions(
                    session,
                    keep_version_id=version.id,
                    retired_at=now,
                )
                version.supersedes_version_id = superseded_version_id

            for rule_payload in normalized_rules:
                session.add(TagRule(rule_version_id=version.id, **rule_payload))
            session.flush()

            result = self._serialize_rule_version(session, version.id)

        self._audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                object_type="tag_rule_version",
                object_id=version_code,
                action="create",
                result="success",
                request_id=request_id,
                event_payload={
                    "status": result["status"],
                    "release_kind": result["release_kind"],
                    "rule_count": result["rule_count"],
                    "dictionary_size": result["dictionary_size"],
                    "auto_activate": auto_activate,
                },
            )
        )

        if auto_activate:
            self._audit_service.safe_write_event(
                AuditEvent(
                    actor_id=actor_id,
                    actor_type=actor_type,
                    object_type="tag_rule_version",
                    object_id=version_code,
                    action="activate",
                    result="success",
                    request_id=request_id,
                    event_payload={
                        "supersedes_version_code": result["supersedes_version_code"],
                        "activated_at": result["activated_at"],
                    },
                )
            )

        return result

    def activate_rule_version(
        self,
        version_code: str,
        *,
        actor_id: str | None = None,
        actor_type: str | None = "user",
        request_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_version_code = _normalize_version_code(version_code)
        now = _now_utc()

        with session_scope() as session:
            version = session.scalar(
                select(TagRuleVersion)
                .options(selectinload(TagRuleVersion.rules))
                .where(TagRuleVersion.version_code == normalized_version_code)
            )
            if version is None:
                raise ValueError(f"version_code {normalized_version_code} 不存在。")

            if version.status == ACTIVE_VERSION_STATUS:
                return self._serialize_loaded_rule_version(session, version)

            if version.status != DRAFT_VERSION_STATUS:
                raise ValueError("仅 draft 状态的规则版本允许直接激活；历史版本请使用 rollback_to_version。")

            rules = [_serialize_rule(rule) for rule in version.rules]
            self._ensure_version_activatable(
                dictionary_snapshot=deepcopy(version.dictionary_snapshot),
                rules=rules,
            )

            superseded_version_id = self._retire_active_versions(
                session,
                keep_version_id=version.id,
                retired_at=now,
            )
            version.status = ACTIVE_VERSION_STATUS
            version.activated_at = now
            version.activated_by = _clean_text(actor_id)
            version.supersedes_version_id = superseded_version_id
            session.flush()

            result = self._serialize_loaded_rule_version(session, version)

        self._audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                object_type="tag_rule_version",
                object_id=normalized_version_code,
                action="activate",
                result="success",
                request_id=request_id,
                event_payload={
                    "supersedes_version_code": result["supersedes_version_code"],
                    "activated_at": result["activated_at"],
                },
            )
        )
        return result

    def rollback_to_version(
        self,
        *,
        target_version_code: str,
        rollback_version_code: str,
        change_reason: str,
        actor_id: str | None = None,
        actor_type: str | None = "user",
        request_id: str | None = None,
        evidence_summary: str | None = None,
        impact_summary: str | None = None,
        rollback_plan: str | None = None,
        version_notes: str | None = None,
    ) -> dict[str, Any]:
        normalized_target_version_code = _normalize_version_code(target_version_code)
        normalized_rollback_version_code = _normalize_version_code(rollback_version_code)
        normalized_change_reason = _clean_text(change_reason)
        if normalized_change_reason is None:
            raise ValueError("change_reason 不能为空。")

        now = _now_utc()

        with session_scope() as session:
            existing = session.scalar(
                select(TagRuleVersion.id).where(
                    TagRuleVersion.version_code == normalized_rollback_version_code
                )
            )
            if existing is not None:
                raise ValueError(f"rollback_version_code {normalized_rollback_version_code} 已存在。")

            target_version = session.scalar(
                select(TagRuleVersion)
                .options(selectinload(TagRuleVersion.rules))
                .where(TagRuleVersion.version_code == normalized_target_version_code)
            )
            if target_version is None:
                raise ValueError(f"target_version_code {normalized_target_version_code} 不存在。")

            cloned_rules = [_serialize_rule(rule) for rule in target_version.rules]
            dictionary_snapshot = deepcopy(target_version.dictionary_snapshot)
            config_payload = deepcopy(target_version.config_payload)
            self._ensure_version_activatable(
                dictionary_snapshot=dictionary_snapshot,
                rules=cloned_rules,
            )

            rollback_version = TagRuleVersion(
                version_code=normalized_rollback_version_code,
                status=ACTIVE_VERSION_STATUS,
                release_kind="rollback",
                base_version_id=target_version.id,
                change_reason=normalized_change_reason,
                evidence_summary=_clean_text(evidence_summary),
                impact_summary=_clean_text(impact_summary),
                rollback_plan=_clean_text(rollback_plan),
                version_notes=_clean_text(version_notes),
                dictionary_snapshot=dictionary_snapshot,
                config_payload=config_payload,
                checksum=_compute_checksum(
                    dictionary_snapshot=dictionary_snapshot,
                    config_payload=config_payload,
                    rules=cloned_rules,
                ),
                created_by=_clean_text(actor_id),
                activated_by=_clean_text(actor_id),
                activated_at=now,
            )
            session.add(rollback_version)
            session.flush()

            superseded_version_id = self._retire_active_versions(
                session,
                keep_version_id=rollback_version.id,
                retired_at=now,
            )
            rollback_version.supersedes_version_id = superseded_version_id

            for rule_payload in cloned_rules:
                session.add(
                    TagRule(
                        rule_version_id=rollback_version.id,
                        rule_code=rule_payload["rule_code"],
                        rule_name=rule_payload["rule_name"],
                        rule_kind=rule_payload["rule_kind"],
                        action_type=rule_payload["action_type"],
                        target_tag_code=rule_payload["target_tag_code"],
                        priority=rule_payload["priority"],
                        enabled=rule_payload["enabled"],
                        match_scope=rule_payload["match_scope"],
                        match_operator=rule_payload["match_operator"],
                        match_payload=rule_payload["match_payload"],
                        effect_payload=rule_payload["effect_payload"],
                        notes=rule_payload["notes"],
                    )
                )
            session.flush()

            result = self._serialize_rule_version(session, rollback_version.id)

        self._audit_service.safe_write_event(
            AuditEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                object_type="tag_rule_version",
                object_id=normalized_rollback_version_code,
                action="rollback",
                result="success",
                request_id=request_id,
                event_payload={
                    "target_version_code": normalized_target_version_code,
                    "supersedes_version_code": result["supersedes_version_code"],
                    "activated_at": result["activated_at"],
                },
            )
        )
        return result

    def list_rule_versions(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with session_scope() as session:
            stmt = (
                select(TagRuleVersion)
                .options(selectinload(TagRuleVersion.rules))
                .order_by(TagRuleVersion.created_at.desc())
                .limit(limit)
            )
            versions = session.scalars(stmt).all()
            return [self._serialize_loaded_rule_version(session, version) for version in versions]

    def get_active_rule_version(self) -> dict[str, Any] | None:
        with session_scope() as session:
            version = session.scalar(
                select(TagRuleVersion)
                .options(selectinload(TagRuleVersion.rules))
                .where(TagRuleVersion.status == ACTIVE_VERSION_STATUS)
                .order_by(TagRuleVersion.activated_at.desc(), TagRuleVersion.created_at.desc())
            )
            if version is None:
                return None
            return self._serialize_loaded_rule_version(session, version)

    def get_rule_version(self, version_code: str) -> dict[str, Any] | None:
        normalized_version_code = _normalize_version_code(version_code)
        with session_scope() as session:
            version = session.scalar(
                select(TagRuleVersion)
                .options(selectinload(TagRuleVersion.rules))
                .where(TagRuleVersion.version_code == normalized_version_code)
            )
            if version is None:
                return None
            return self._serialize_loaded_rule_version(session, version)

    @staticmethod
    def _build_dictionary_snapshot(session) -> list[dict[str, Any]]:
        entries = session.scalars(
            select(TagDictionaryEntry)
            .where(TagDictionaryEntry.is_active.is_(True))
            .order_by(
                TagDictionaryEntry.tag_type.asc(),
                TagDictionaryEntry.dimension.asc(),
                TagDictionaryEntry.sort_order.asc(),
                TagDictionaryEntry.tag_code.asc(),
            )
        ).all()
        return [_serialize_tag_definition(entry) for entry in entries]

    @staticmethod
    def _ensure_version_activatable(
        *,
        dictionary_snapshot: list[dict[str, Any]],
        rules: list[dict[str, Any]],
    ) -> None:
        if not dictionary_snapshot:
            raise ValueError("激活规则版本前，至少需要一个启用中的标签字典条目。")
        if not any(rule.get("enabled") for rule in rules):
            raise ValueError("激活规则版本前，至少需要一条启用中的规则。")

    @staticmethod
    def _retire_active_versions(session, *, keep_version_id, retired_at: datetime):
        active_versions = session.scalars(
            select(TagRuleVersion)
            .where(TagRuleVersion.status == ACTIVE_VERSION_STATUS)
            .order_by(TagRuleVersion.activated_at.desc(), TagRuleVersion.created_at.desc())
        ).all()
        superseded_version_id = None
        for active_version in active_versions:
            if active_version.id == keep_version_id:
                continue
            if superseded_version_id is None:
                superseded_version_id = active_version.id
            active_version.status = "superseded"
            active_version.retired_at = retired_at
        return superseded_version_id

    def _serialize_rule_version(self, session, version_id) -> dict[str, Any]:
        version = session.scalar(
            select(TagRuleVersion)
            .options(selectinload(TagRuleVersion.rules))
            .where(TagRuleVersion.id == version_id)
        )
        if version is None:
            raise ValueError("规则版本不存在。")
        return self._serialize_loaded_rule_version(session, version)

    @staticmethod
    def _serialize_loaded_rule_version(session, version: TagRuleVersion) -> dict[str, Any]:
        reference_ids = [value for value in (version.base_version_id, version.supersedes_version_id) if value is not None]
        reference_map: dict[Any, str] = {}
        if reference_ids:
            reference_map = {
                item.id: item.version_code
                for item in session.scalars(
                    select(TagRuleVersion).where(TagRuleVersion.id.in_(reference_ids))
                ).all()
            }

        ordered_rules = sorted(version.rules, key=lambda item: (item.priority, item.rule_code))
        return {
            "version_code": version.version_code,
            "status": version.status,
            "release_kind": version.release_kind,
            "base_version_code": reference_map.get(version.base_version_id),
            "supersedes_version_code": reference_map.get(version.supersedes_version_id),
            "change_reason": version.change_reason,
            "evidence_summary": version.evidence_summary,
            "impact_summary": version.impact_summary,
            "rollback_plan": version.rollback_plan,
            "version_notes": version.version_notes,
            "checksum": version.checksum,
            "created_by": version.created_by,
            "activated_by": version.activated_by,
            "created_at": version.created_at.isoformat(),
            "updated_at": version.updated_at.isoformat(),
            "activated_at": version.activated_at.isoformat() if version.activated_at else None,
            "retired_at": version.retired_at.isoformat() if version.retired_at else None,
            "dictionary_size": len(version.dictionary_snapshot) if isinstance(version.dictionary_snapshot, list) else 0,
            "dictionary_snapshot": deepcopy(version.dictionary_snapshot),
            "config_payload": deepcopy(version.config_payload),
            "rule_count": len(ordered_rules),
            "rules": [_serialize_rule(rule) for rule in ordered_rules],
        }


@lru_cache
def get_tagging_rule_service() -> TaggingRuleService:
    return TaggingRuleService()
