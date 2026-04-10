"""feat_m5_m6_workflows"""

revision = "20260410_0011"
down_revision = "f52a58536cb6"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recommendation", sa.String(length=16), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=True),
        sa.Column("executed_by", sa.String(length=128), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_runs")),
    )
    with op.batch_alter_table("backtest_runs", schema=None) as batch_op:
        batch_op.create_index("ix_backtest_runs_status_created_at", ["status", "created_at"], unique=False)
        batch_op.create_index(
            "ix_backtest_runs_recommendation_created_at",
            ["recommendation", "created_at"],
            unique=False,
        )

    op.create_table(
        "shadow_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_name", sa.String(length=128), nullable=False),
        sa.Column("risk_state", sa.String(length=32), nullable=False),
        sa.Column("recommendation", sa.String(length=16), nullable=False),
        sa.Column("executed_by", sa.String(length=128), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shadow_runs")),
    )
    with op.batch_alter_table("shadow_runs", schema=None) as batch_op:
        batch_op.create_index(
            "ix_shadow_runs_recommendation_created_at",
            ["recommendation", "created_at"],
            unique=False,
        )

    op.create_table(
        "launch_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=False),
        sa.Column("shadow_run_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["shadow_run_id"], ["shadow_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_launch_reviews")),
    )
    with op.batch_alter_table("launch_reviews", schema=None) as batch_op:
        batch_op.create_index("ix_launch_reviews_status_created_at", ["status", "created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("launch_reviews", schema=None) as batch_op:
        batch_op.drop_index("ix_launch_reviews_status_created_at")
    op.drop_table("launch_reviews")

    with op.batch_alter_table("shadow_runs", schema=None) as batch_op:
        batch_op.drop_index("ix_shadow_runs_recommendation_created_at")
    op.drop_table("shadow_runs")

    with op.batch_alter_table("backtest_runs", schema=None) as batch_op:
        batch_op.drop_index("ix_backtest_runs_recommendation_created_at")
        batch_op.drop_index("ix_backtest_runs_status_created_at")
    op.drop_table("backtest_runs")
