"""add market scoring results table

Revision ID: 20260403_0006
Revises: 20260329_0005
Create Date: 2026-04-03

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260403_0006"
down_revision = "20260329_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 market_scoring_results 表
    op.create_table(
        "market_scoring_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("market_ref_id", sa.Uuid(), nullable=False),
        sa.Column("classification_result_id", sa.Uuid(), nullable=True),
        sa.Column("clarity_score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("resolution_objectivity_score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("overall_score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("admission_recommendation", sa.String(length=32), nullable=False),
        sa.Column("rejection_reason_code", sa.String(length=64), nullable=True),
        sa.Column(
            "scoring_details",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["market_ref_id"], ["markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["classification_result_id"],
            ["market_classification_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 创建索引
    op.create_index(
        "uq_market_scoring_results_market_ref_id_classification_result_id",
        "market_scoring_results",
        ["market_ref_id", "classification_result_id"],
        unique=True,
    )
    op.create_index(
        "ix_market_scoring_results_admission_recommendation",
        "market_scoring_results",
        ["admission_recommendation"],
    )
    op.create_index(
        "ix_market_scoring_results_scored_at",
        "market_scoring_results",
        ["scored_at"],
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index("ix_market_scoring_results_scored_at", table_name="market_scoring_results")
    op.drop_index("ix_market_scoring_results_admission_recommendation", table_name="market_scoring_results")
    op.drop_index(
        "uq_market_scoring_results_market_ref_id_classification_result_id",
        table_name="market_scoring_results",
    )

    # 删除表
    op.drop_table("market_scoring_results")
