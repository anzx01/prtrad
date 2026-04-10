"""fix_m2_report_created_at_default_for_sqlite"""

revision = "20260410_0012"
down_revision = "20260410_0011"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    with op.batch_alter_table("m2_reports", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        )


def downgrade() -> None:
    with op.batch_alter_table("m2_reports", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.text("now()"),
        )
