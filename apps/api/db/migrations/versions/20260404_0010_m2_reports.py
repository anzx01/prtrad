"""m2 reports table

Revision ID: 20260404_0010
Revises: 20260404_0009
Create Date: 2026-04-04 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260404_0010'
down_revision: Union[str, None] = '20260404_0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create m2_reports table
    op.create_table(
        'm2_reports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('report_type', sa.String(length=32), nullable=False),
        sa.Column('report_period_start', sa.Date(), nullable=False),
        sa.Column('report_period_end', sa.Date(), nullable=False),
        sa.Column('report_data', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('generated_by', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_type', 'report_period_start', 'report_period_end',
                          name='uq_m2_reports_type_period')
    )
    op.create_index('ix_m2_reports_type_period', 'm2_reports', ['report_type', 'report_period_end'],
                   postgresql_using='btree')


def downgrade() -> None:
    op.drop_index('ix_m2_reports_type_period', table_name='m2_reports')
    op.drop_table('m2_reports')
