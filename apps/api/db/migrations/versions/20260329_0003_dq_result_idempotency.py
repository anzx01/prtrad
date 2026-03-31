"""add dq result idempotency index"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0003"
down_revision = "20260328_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"]: index for index in inspector.get_indexes("data_quality_results")}

    if "ix_data_quality_results_market_ref_id_checked_at" in indexes:
        op.drop_index("ix_data_quality_results_market_ref_id_checked_at", table_name="data_quality_results")

    if "uq_data_quality_results_market_ref_id_checked_at_rule_version" not in indexes:
        op.create_index(
            "uq_data_quality_results_market_ref_id_checked_at_rule_version",
            "data_quality_results",
            ["market_ref_id", "checked_at", "rule_version"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"]: index for index in inspector.get_indexes("data_quality_results")}

    if "uq_data_quality_results_market_ref_id_checked_at_rule_version" in indexes:
        op.drop_index(
            "uq_data_quality_results_market_ref_id_checked_at_rule_version",
            table_name="data_quality_results",
        )

    if "ix_data_quality_results_market_ref_id_checked_at" not in indexes:
        op.create_index(
            "ix_data_quality_results_market_ref_id_checked_at",
            "data_quality_results",
            ["market_ref_id", "checked_at"],
            unique=False,
        )
