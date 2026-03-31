from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TagDefinitionInput:
    tag_code: str
    tag_name: str
    tag_type: str
    dimension: str
    description: str | None = None
    aliases: list[str] = field(default_factory=list)
    tag_metadata: dict[str, Any] = field(default_factory=dict)
    sort_order: int = 100
    is_active: bool = True


@dataclass(slots=True)
class TagRuleInput:
    rule_code: str
    rule_name: str
    rule_kind: str
    action_type: str
    target_tag_code: str | None = None
    priority: int = 100
    enabled: bool = True
    match_scope: list[str] = field(default_factory=list)
    match_operator: str = "contains_any"
    match_payload: dict[str, Any] = field(default_factory=dict)
    effect_payload: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None


@dataclass(slots=True)
class TagRuleVersionCreateInput:
    version_code: str
    change_reason: str
    rules: list[TagRuleInput] = field(default_factory=list)
    config_payload: dict[str, Any] = field(default_factory=dict)
    base_version_code: str | None = None
    evidence_summary: str | None = None
    impact_summary: str | None = None
    rollback_plan: str | None = None
    version_notes: str | None = None
