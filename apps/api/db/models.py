import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid, func
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
        Index("ix_data_quality_results_market_ref_id_checked_at", "market_ref_id", "checked_at"),
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
