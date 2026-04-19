"""feat_trading_order_records"""

revision = "20260419_0014"
down_revision = "20260419_0013"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "trading_order_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trading_runtime_state_id", sa.Uuid(), nullable=True),
        sa.Column("market_ref_id", sa.Uuid(), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("market_id_snapshot", sa.String(length=128), nullable=False),
        sa.Column("question_snapshot", sa.Text(), nullable=False),
        sa.Column("outcome_side", sa.String(length=8), nullable=False),
        sa.Column("token_id", sa.String(length=256), nullable=True),
        sa.Column("order_price", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("order_size", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("notional_amount", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("expected_net_ev", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("requested_by", sa.String(length=128), nullable=True),
        sa.Column("provider_order_id", sa.String(length=128), nullable=True),
        sa.Column("failure_reason_code", sa.String(length=64), nullable=True),
        sa.Column("failure_reason_text", sa.Text(), nullable=True),
        sa.Column("execution_details", sa.JSON(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["market_ref_id"],
            ["markets.id"],
            name=op.f("fk_trading_order_records_market_ref_id_markets"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["trading_runtime_state_id"],
            ["trading_runtime_states.id"],
            name=op.f("fk_trading_order_records_trading_runtime_state_id_trading_runtime_states"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trading_order_records")),
    )
    with op.batch_alter_table("trading_order_records", schema=None) as batch_op:
        batch_op.create_index("ix_trading_order_records_market_id_snapshot", ["market_id_snapshot"], unique=False)
        batch_op.create_index("ix_trading_order_records_market_ref_id", ["market_ref_id"], unique=False)
        batch_op.create_index(
            "ix_trading_order_records_market_ref_id_created_at",
            ["market_ref_id", "created_at"],
            unique=False,
        )
        batch_op.create_index("ix_trading_order_records_mode", ["mode"], unique=False)
        batch_op.create_index("ix_trading_order_records_provider_order_id", ["provider_order_id"], unique=False)
        batch_op.create_index("ix_trading_order_records_status", ["status"], unique=False)
        batch_op.create_index(
            "ix_trading_order_records_status_mode",
            ["status", "mode"],
            unique=False,
        )
        batch_op.create_index("ix_trading_order_records_trading_runtime_state_id", ["trading_runtime_state_id"], unique=False)
        batch_op.create_index("ix_trading_order_records_failure_reason_code", ["failure_reason_code"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("trading_order_records", schema=None) as batch_op:
        batch_op.drop_index("ix_trading_order_records_failure_reason_code")
        batch_op.drop_index("ix_trading_order_records_trading_runtime_state_id")
        batch_op.drop_index("ix_trading_order_records_status_mode")
        batch_op.drop_index("ix_trading_order_records_status")
        batch_op.drop_index("ix_trading_order_records_provider_order_id")
        batch_op.drop_index("ix_trading_order_records_mode")
        batch_op.drop_index("ix_trading_order_records_market_ref_id_created_at")
        batch_op.drop_index("ix_trading_order_records_market_ref_id")
        batch_op.drop_index("ix_trading_order_records_market_id_snapshot")
    op.drop_table("trading_order_records")
