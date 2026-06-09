"""feat_trading_runtime_state"""

revision = "20260419_0013"
down_revision = "20260410_0012"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "trading_runtime_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_by", sa.String(length=128), nullable=True),
        sa.Column("stopped_by", sa.String(length=128), nullable=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stop_reason_code", sa.String(length=64), nullable=True),
        sa.Column("last_stop_reason_text", sa.Text(), nullable=True),
        sa.Column("last_stop_was_automatic", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_guard_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trading_runtime_states")),
    )
    with op.batch_alter_table("trading_runtime_states", schema=None) as batch_op:
        batch_op.create_index(
            "ix_trading_runtime_states_status_mode",
            ["status", "mode"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("trading_runtime_states", schema=None) as batch_op:
        batch_op.drop_index("ix_trading_runtime_states_status_mode")
    op.drop_table("trading_runtime_states")
