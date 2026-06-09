"""feat_paper_positions"""

revision = "20260609_0015"
down_revision = "20260419_0014"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "paper_positions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("market_ref_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("strategy_version", sa.String(length=64), nullable=True),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("size", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("entry_notional", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("mark_price", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("mark_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(precision=18, scale=6), nullable=False, server_default=sa.text("0")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_price", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("exit_reason", sa.String(length=64), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(precision=18, scale=6), nullable=True),
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
            ["candidate_id"],
            ["netev_candidates.id"],
            name=op.f("fk_paper_positions_candidate_id_netev_candidates"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["market_ref_id"],
            ["markets.id"],
            name=op.f("fk_paper_positions_market_ref_id_markets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["trading_order_records.id"],
            name=op.f("fk_paper_positions_order_id_trading_order_records"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_paper_positions")),
    )
    with op.batch_alter_table("paper_positions", schema=None) as batch_op:
        batch_op.create_index("ix_paper_positions_candidate_id", ["candidate_id"], unique=False)
        batch_op.create_index("ix_paper_positions_market_ref_id_status", ["market_ref_id", "status"], unique=False)
        batch_op.create_index("ix_paper_positions_order_id", ["order_id"], unique=False)
        batch_op.create_index("ix_paper_positions_status_opened_at", ["status", "opened_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("paper_positions", schema=None) as batch_op:
        batch_op.drop_index("ix_paper_positions_status_opened_at")
        batch_op.drop_index("ix_paper_positions_order_id")
        batch_op.drop_index("ix_paper_positions_market_ref_id_status")
        batch_op.drop_index("ix_paper_positions_candidate_id")
    op.drop_table("paper_positions")
