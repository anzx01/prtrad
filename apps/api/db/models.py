import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Market(TimestampMixin, Base):
    __tablename__ = "markets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    condition_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    creation_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    category_raw: Mapped[str | None] = mapped_column(String(128), nullable=True)
    related_tags: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    outcomes: Mapped[list | None] = mapped_column(json_type(), nullable=True)
    clob_token_ids: Mapped[list | None] = mapped_column(json_type(), nullable=True)
    source_payload: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    snapshots: Mapped[list["MarketSnapshot"]] = relationship(back_populates="market", cascade="all, delete-orphan")
    dq_results: Mapped[list["DataQualityResult"]] = relationship(back_populates="market", cascade="all, delete-orphan")
    decision_logs: Mapped[list["DecisionLog"]] = relationship(back_populates="market", cascade="all, delete-orphan")
    classification_results: Mapped[list["MarketClassificationResult"]] = relationship(
        back_populates="market", cascade="all, delete-orphan"
    )
    review_tasks: Mapped[list["MarketReviewTask"]] = relationship(
        back_populates="market", cascade="all, delete-orphan"
    )


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint("market_ref_id", "snapshot_time", name="uq_market_snapshots_market_ref_id_snapshot_time"),
        Index("ix_market_snapshots_market_ref_id_snapshot_time", "market_ref_id", "snapshot_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_ref_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    best_bid_no: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    best_ask_no: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    best_bid_yes: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    best_ask_yes: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    last_trade_price_no: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    spread: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    top_of_book_depth: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    cumulative_depth_at_target_size: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    trade_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traded_volume: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    last_trade_age_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    market: Mapped["Market"] = relationship(back_populates="snapshots")


class DataQualityResult(Base):
    __tablename__ = "data_quality_results"
    __table_args__ = (
        Index(
            "uq_data_quality_results_market_ref_id_checked_at_rule_version",
            "market_ref_id",
            "checked_at",
            "rule_version",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_ref_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=False
    )
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_details: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    market: Mapped["Market"] = relationship(back_populates="dq_results")


class DecisionLog(Base):
    __tablename__ = "decision_logs"
    __table_args__ = (
        Index("ix_decision_logs_market_ref_id_created_at", "market_ref_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("markets.id", ondelete="SET NULL"), nullable=True
    )
    signal_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    primary_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secondary_reason_codes: Mapped[list | None] = mapped_column(json_type(), nullable=True)
    payload: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    market: Mapped["Market"] = relationship(back_populates="decision_logs")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_object_type_object_id", "object_type", "object_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    actor_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    event_payload: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TagDictionaryEntry(TimestampMixin, Base):
    __tablename__ = "tag_dictionary_entries"
    __table_args__ = (
        UniqueConstraint("tag_code", name="uq_tag_dictionary_entries_tag_code"),
        Index("ix_tag_dictionary_entries_tag_type_dimension", "tag_type", "dimension"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tag_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tag_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases: Mapped[list | None] = mapped_column(json_type(), nullable=True)
    tag_metadata: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TagRuleVersion(TimestampMixin, Base):
    __tablename__ = "tag_rule_versions"
    __table_args__ = (
        UniqueConstraint("version_code", name="uq_tag_rule_versions_version_code"),
        Index("ix_tag_rule_versions_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    release_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="standard", index=True)
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tag_rule_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supersedes_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tag_rule_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    dictionary_snapshot: Mapped[dict | list] = mapped_column(json_type(), nullable=False)
    config_payload: Mapped[dict | list] = mapped_column(json_type(), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rules: Mapped[list["TagRule"]] = relationship(back_populates="rule_version", cascade="all, delete-orphan")


class TagRule(TimestampMixin, Base):
    __tablename__ = "tag_rules"
    __table_args__ = (
        UniqueConstraint("rule_version_id", "rule_code", name="uq_tag_rules_rule_version_id_rule_code"),
        Index("ix_tag_rules_rule_version_id_priority", "rule_version_id", "priority"),
        Index("ix_tag_rules_target_tag_code_enabled", "target_tag_code", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tag_rule_versions.id", ondelete="CASCADE"), nullable=False
    )
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_tag_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    match_scope: Mapped[dict | list] = mapped_column(json_type(), nullable=False)
    match_operator: Mapped[str] = mapped_column(String(32), nullable=False)
    match_payload: Mapped[dict | list] = mapped_column(json_type(), nullable=False)
    effect_payload: Mapped[dict | list] = mapped_column(json_type(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule_version: Mapped["TagRuleVersion"] = relationship(back_populates="rules")


class MarketClassificationResult(Base):
    __tablename__ = "market_classification_results"
    __table_args__ = (
        Index(
            "uq_market_classification_results_market_ref_id_rule_version_source_fingerprint",
            "market_ref_id",
            "rule_version",
            "source_fingerprint",
            unique=True,
        ),
        Index("ix_market_classification_results_status_classified_at", "classification_status", "classified_at"),
        Index("ix_market_classification_results_market_ref_id_classified_at", "market_ref_id", "classified_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_ref_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=False
    )
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    classification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    primary_category_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    admission_bucket_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    result_details: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    market: Mapped["Market"] = relationship(back_populates="classification_results")
    assignments: Mapped[list["MarketTagAssignment"]] = relationship(
        back_populates="classification_result", cascade="all, delete-orphan"
    )
    explanations: Mapped[list["MarketTagExplanation"]] = relationship(
        back_populates="classification_result", cascade="all, delete-orphan"
    )
    review_task: Mapped["MarketReviewTask | None"] = relationship(
        back_populates="classification_result",
        cascade="all, delete-orphan",
        uselist=False,
    )


class MarketTagAssignment(Base):
    __tablename__ = "market_tag_assignments"
    __table_args__ = (
        UniqueConstraint(
            "classification_result_id",
            "tag_code",
            name="uq_market_tag_assignments_classification_result_id_tag_code",
        ),
        Index("ix_market_tag_assignments_market_ref_id_tag_code", "market_ref_id", "tag_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("market_classification_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    market_ref_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=False
    )
    tag_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tag_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    assignment_role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    assignment_metadata: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    classification_result: Mapped["MarketClassificationResult"] = relationship(back_populates="assignments")


class MarketTagExplanation(Base):
    __tablename__ = "market_tag_explanations"
    __table_args__ = (
        Index(
            "ix_market_tag_explanations_classification_result_id_rule_code",
            "classification_result_id",
            "rule_code",
        ),
        Index("ix_market_tag_explanations_market_ref_id_explanation_type", "market_ref_id", "explanation_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("market_classification_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    market_ref_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=False
    )
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_tag_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    explanation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence_delta: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    explanation_payload: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    classification_result: Mapped["MarketClassificationResult"] = relationship(back_populates="explanations")


class MarketReviewTask(TimestampMixin, Base):
    __tablename__ = "market_review_tasks"
    __table_args__ = (
        UniqueConstraint("classification_result_id", name="uq_market_review_tasks_classification_result_id"),
        Index("ix_market_review_tasks_queue_status_created_at", "queue_status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_ref_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=False
    )
    classification_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("market_classification_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    queue_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    review_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_payload: Mapped[dict | list | None] = mapped_column(json_type(), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    market: Mapped["Market"] = relationship(back_populates="review_tasks")
    classification_result: Mapped["MarketClassificationResult"] = relationship(back_populates="review_task")
