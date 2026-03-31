"""add market auto tagging result tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_0005"
down_revision = "20260329_0004"
branch_labels = None
depends_on = None


def json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def uuid_type():
    return sa.UUID().with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    op.create_table(
        "market_classification_results",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("market_ref_id", uuid_type(), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("classification_status", sa.String(length=32), nullable=False),
        sa.Column("primary_category_code", sa.String(length=64), nullable=True),
        sa.Column("admission_bucket_code", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=True),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("conflict_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason_code", sa.String(length=64), nullable=True),
        sa.Column("result_details", json_type(), nullable=True),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["market_ref_id"],
            ["markets.id"],
            name="fk_market_classification_results_market_ref_id_markets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_classification_results"),
    )
    op.create_index(
        "uq_market_classification_results_market_ref_id_rule_version_source_fingerprint",
        "market_classification_results",
        ["market_ref_id", "rule_version", "source_fingerprint"],
        unique=True,
    )
    op.create_index(
        "ix_market_classification_results_market_ref_id_classified_at",
        "market_classification_results",
        ["market_ref_id", "classified_at"],
        unique=False,
    )
    op.create_index(
        "ix_market_classification_results_status_classified_at",
        "market_classification_results",
        ["classification_status", "classified_at"],
        unique=False,
    )
    op.create_index(
        "ix_market_classification_results_rule_version",
        "market_classification_results",
        ["rule_version"],
        unique=False,
    )
    op.create_index(
        "ix_market_classification_results_classification_status",
        "market_classification_results",
        ["classification_status"],
        unique=False,
    )
    op.create_index(
        "ix_market_classification_results_primary_category_code",
        "market_classification_results",
        ["primary_category_code"],
        unique=False,
    )
    op.create_index(
        "ix_market_classification_results_admission_bucket_code",
        "market_classification_results",
        ["admission_bucket_code"],
        unique=False,
    )
    op.create_index(
        "ix_market_classification_results_failure_reason_code",
        "market_classification_results",
        ["failure_reason_code"],
        unique=False,
    )

    op.create_table(
        "market_tag_assignments",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("classification_result_id", uuid_type(), nullable=False),
        sa.Column("market_ref_id", uuid_type(), nullable=False),
        sa.Column("tag_code", sa.String(length=64), nullable=False),
        sa.Column("tag_type", sa.String(length=32), nullable=False),
        sa.Column("assignment_role", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=True),
        sa.Column("assignment_metadata", json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["classification_result_id"],
            ["market_classification_results.id"],
            name="fk_market_tag_assignments_classification_result_id_market_classification_results",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["market_ref_id"],
            ["markets.id"],
            name="fk_market_tag_assignments_market_ref_id_markets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_tag_assignments"),
        sa.UniqueConstraint(
            "classification_result_id",
            "tag_code",
            name="uq_market_tag_assignments_classification_result_id_tag_code",
        ),
    )
    op.create_index("ix_market_tag_assignments_tag_code", "market_tag_assignments", ["tag_code"], unique=False)
    op.create_index("ix_market_tag_assignments_tag_type", "market_tag_assignments", ["tag_type"], unique=False)
    op.create_index(
        "ix_market_tag_assignments_assignment_role",
        "market_tag_assignments",
        ["assignment_role"],
        unique=False,
    )
    op.create_index(
        "ix_market_tag_assignments_market_ref_id_tag_code",
        "market_tag_assignments",
        ["market_ref_id", "tag_code"],
        unique=False,
    )

    op.create_table(
        "market_tag_explanations",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("classification_result_id", uuid_type(), nullable=False),
        sa.Column("market_ref_id", uuid_type(), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("rule_name", sa.String(length=128), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("target_tag_code", sa.String(length=64), nullable=True),
        sa.Column("explanation_type", sa.String(length=32), nullable=False),
        sa.Column("confidence_delta", sa.Numeric(8, 4), nullable=True),
        sa.Column("explanation_payload", json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["classification_result_id"],
            ["market_classification_results.id"],
            name="fk_market_tag_explanations_classification_result_id_market_classification_results",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["market_ref_id"],
            ["markets.id"],
            name="fk_market_tag_explanations_market_ref_id_markets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_tag_explanations"),
    )
    op.create_index("ix_market_tag_explanations_rule_code", "market_tag_explanations", ["rule_code"], unique=False)
    op.create_index(
        "ix_market_tag_explanations_action_type",
        "market_tag_explanations",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        "ix_market_tag_explanations_target_tag_code",
        "market_tag_explanations",
        ["target_tag_code"],
        unique=False,
    )
    op.create_index(
        "ix_market_tag_explanations_explanation_type",
        "market_tag_explanations",
        ["explanation_type"],
        unique=False,
    )
    op.create_index(
        "ix_market_tag_explanations_classification_result_id_rule_code",
        "market_tag_explanations",
        ["classification_result_id", "rule_code"],
        unique=False,
    )
    op.create_index(
        "ix_market_tag_explanations_market_ref_id_explanation_type",
        "market_tag_explanations",
        ["market_ref_id", "explanation_type"],
        unique=False,
    )

    op.create_table(
        "market_review_tasks",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("market_ref_id", uuid_type(), nullable=False),
        sa.Column("classification_result_id", uuid_type(), nullable=False),
        sa.Column("queue_status", sa.String(length=32), nullable=False),
        sa.Column("review_reason_code", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("assigned_to", sa.String(length=128), nullable=True),
        sa.Column("review_payload", json_type(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["market_ref_id"],
            ["markets.id"],
            name="fk_market_review_tasks_market_ref_id_markets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["classification_result_id"],
            ["market_classification_results.id"],
            name="fk_market_review_tasks_classification_result_id_market_classification_results",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_review_tasks"),
        sa.UniqueConstraint(
            "classification_result_id",
            name="uq_market_review_tasks_classification_result_id",
        ),
    )
    op.create_index("ix_market_review_tasks_queue_status", "market_review_tasks", ["queue_status"], unique=False)
    op.create_index(
        "ix_market_review_tasks_review_reason_code",
        "market_review_tasks",
        ["review_reason_code"],
        unique=False,
    )
    op.create_index(
        "ix_market_review_tasks_queue_status_created_at",
        "market_review_tasks",
        ["queue_status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_market_review_tasks_queue_status_created_at", table_name="market_review_tasks")
    op.drop_index("ix_market_review_tasks_review_reason_code", table_name="market_review_tasks")
    op.drop_index("ix_market_review_tasks_queue_status", table_name="market_review_tasks")
    op.drop_table("market_review_tasks")

    op.drop_index(
        "ix_market_tag_explanations_market_ref_id_explanation_type",
        table_name="market_tag_explanations",
    )
    op.drop_index(
        "ix_market_tag_explanations_classification_result_id_rule_code",
        table_name="market_tag_explanations",
    )
    op.drop_index("ix_market_tag_explanations_explanation_type", table_name="market_tag_explanations")
    op.drop_index("ix_market_tag_explanations_target_tag_code", table_name="market_tag_explanations")
    op.drop_index("ix_market_tag_explanations_action_type", table_name="market_tag_explanations")
    op.drop_index("ix_market_tag_explanations_rule_code", table_name="market_tag_explanations")
    op.drop_table("market_tag_explanations")

    op.drop_index("ix_market_tag_assignments_market_ref_id_tag_code", table_name="market_tag_assignments")
    op.drop_index("ix_market_tag_assignments_assignment_role", table_name="market_tag_assignments")
    op.drop_index("ix_market_tag_assignments_tag_type", table_name="market_tag_assignments")
    op.drop_index("ix_market_tag_assignments_tag_code", table_name="market_tag_assignments")
    op.drop_table("market_tag_assignments")

    op.drop_index(
        "ix_market_classification_results_failure_reason_code",
        table_name="market_classification_results",
    )
    op.drop_index(
        "ix_market_classification_results_admission_bucket_code",
        table_name="market_classification_results",
    )
    op.drop_index(
        "ix_market_classification_results_primary_category_code",
        table_name="market_classification_results",
    )
    op.drop_index(
        "ix_market_classification_results_classification_status",
        table_name="market_classification_results",
    )
    op.drop_index("ix_market_classification_results_rule_version", table_name="market_classification_results")
    op.drop_index(
        "ix_market_classification_results_status_classified_at",
        table_name="market_classification_results",
    )
    op.drop_index(
        "ix_market_classification_results_market_ref_id_classified_at",
        table_name="market_classification_results",
    )
    op.drop_index(
        "uq_market_classification_results_market_ref_id_rule_version_source_fingerprint",
        table_name="market_classification_results",
    )
    op.drop_table("market_classification_results")
