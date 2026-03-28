"""create core schema v1"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260328_0001"
down_revision = None
branch_labels = None
depends_on = None


def json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def uuid_type():
    return sa.UUID().with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    op.create_table(
        "markets",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resolution_criteria", sa.Text(), nullable=True),
        sa.Column("creation_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_resolution", sa.String(length=32), nullable=True),
        sa.Column("market_status", sa.String(length=64), nullable=True),
        sa.Column("category_raw", sa.String(length=128), nullable=True),
        sa.Column("related_tags", json_type(), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_markets"),
        sa.UniqueConstraint("market_id", name="uq_markets_market_id"),
    )
    op.create_index("ix_markets_market_id", "markets", ["market_id"], unique=False)
    op.create_index("ix_markets_event_id", "markets", ["event_id"], unique=False)
    op.create_index("ix_markets_market_status", "markets", ["market_status"], unique=False)

    op.create_table(
        "market_snapshots",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("market_ref_id", uuid_type(), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("best_bid_no", sa.Numeric(12, 6), nullable=True),
        sa.Column("best_ask_no", sa.Numeric(12, 6), nullable=True),
        sa.Column("best_bid_yes", sa.Numeric(12, 6), nullable=True),
        sa.Column("best_ask_yes", sa.Numeric(12, 6), nullable=True),
        sa.Column("last_trade_price_no", sa.Numeric(12, 6), nullable=True),
        sa.Column("spread", sa.Numeric(12, 6), nullable=True),
        sa.Column("top_of_book_depth", sa.Numeric(18, 4), nullable=True),
        sa.Column("cumulative_depth_at_target_size", sa.Numeric(18, 4), nullable=True),
        sa.Column("trade_count", sa.Integer(), nullable=True),
        sa.Column("traded_volume", sa.Numeric(18, 4), nullable=True),
        sa.Column("last_trade_age_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["market_ref_id"], ["markets.id"], name="fk_market_snapshots_market_ref_id_markets", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_market_snapshots"),
        sa.UniqueConstraint("market_ref_id", "snapshot_time", name="uq_market_snapshots_market_ref_id_snapshot_time"),
    )
    op.create_index(
        "ix_market_snapshots_market_ref_id_snapshot_time",
        "market_snapshots",
        ["market_ref_id", "snapshot_time"],
        unique=False,
    )

    op.create_table(
        "data_quality_results",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("market_ref_id", uuid_type(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Numeric(8, 4), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("result_details", json_type(), nullable=True),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["market_ref_id"], ["markets.id"], name="fk_data_quality_results_market_ref_id_markets", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_data_quality_results"),
    )
    op.create_index("ix_data_quality_results_status", "data_quality_results", ["status"], unique=False)
    op.create_index("ix_data_quality_results_rule_version", "data_quality_results", ["rule_version"], unique=False)
    op.create_index(
        "ix_data_quality_results_market_ref_id_checked_at",
        "data_quality_results",
        ["market_ref_id", "checked_at"],
        unique=False,
    )

    op.create_table(
        "decision_logs",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("market_ref_id", uuid_type(), nullable=True),
        sa.Column("signal_id", sa.String(length=128), nullable=True),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("decision_status", sa.String(length=32), nullable=False),
        sa.Column("primary_reason_code", sa.String(length=64), nullable=True),
        sa.Column("secondary_reason_codes", json_type(), nullable=True),
        sa.Column("payload", json_type(), nullable=True),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("task_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["market_ref_id"], ["markets.id"], name="fk_decision_logs_market_ref_id_markets", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_decision_logs"),
    )
    op.create_index("ix_decision_logs_signal_id", "decision_logs", ["signal_id"], unique=False)
    op.create_index("ix_decision_logs_decision_type", "decision_logs", ["decision_type"], unique=False)
    op.create_index("ix_decision_logs_decision_status", "decision_logs", ["decision_status"], unique=False)
    op.create_index("ix_decision_logs_rule_version", "decision_logs", ["rule_version"], unique=False)
    op.create_index("ix_decision_logs_request_id", "decision_logs", ["request_id"], unique=False)
    op.create_index("ix_decision_logs_task_id", "decision_logs", ["task_id"], unique=False)
    op.create_index(
        "ix_decision_logs_market_ref_id_created_at",
        "decision_logs",
        ["market_ref_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("actor_type", sa.String(length=64), nullable=True),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("task_id", sa.String(length=128), nullable=True),
        sa.Column("event_payload", json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"], unique=False)
    op.create_index("ix_audit_logs_object_type", "audit_logs", ["object_type"], unique=False)
    op.create_index("ix_audit_logs_object_id", "audit_logs", ["object_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_result", "audit_logs", ["result"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)
    op.create_index("ix_audit_logs_task_id", "audit_logs", ["task_id"], unique=False)
    op.create_index(
        "ix_audit_logs_object_type_object_id",
        "audit_logs",
        ["object_type", "object_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_object_type_object_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_task_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_result", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_object_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_object_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_decision_logs_market_ref_id_created_at", table_name="decision_logs")
    op.drop_index("ix_decision_logs_task_id", table_name="decision_logs")
    op.drop_index("ix_decision_logs_request_id", table_name="decision_logs")
    op.drop_index("ix_decision_logs_rule_version", table_name="decision_logs")
    op.drop_index("ix_decision_logs_decision_status", table_name="decision_logs")
    op.drop_index("ix_decision_logs_decision_type", table_name="decision_logs")
    op.drop_index("ix_decision_logs_signal_id", table_name="decision_logs")
    op.drop_table("decision_logs")

    op.drop_index("ix_data_quality_results_market_ref_id_checked_at", table_name="data_quality_results")
    op.drop_index("ix_data_quality_results_rule_version", table_name="data_quality_results")
    op.drop_index("ix_data_quality_results_status", table_name="data_quality_results")
    op.drop_table("data_quality_results")

    op.drop_index("ix_market_snapshots_market_ref_id_snapshot_time", table_name="market_snapshots")
    op.drop_table("market_snapshots")

    op.drop_index("ix_markets_market_status", table_name="markets")
    op.drop_index("ix_markets_event_id", table_name="markets")
    op.drop_index("ix_markets_market_id", table_name="markets")
    op.drop_table("markets")

