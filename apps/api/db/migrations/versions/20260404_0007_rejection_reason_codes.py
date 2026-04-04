"""rejection reason codes

Revision ID: 20260404_0007
Revises: 20260403_0006
Create Date: 2026-04-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260404_0007'
down_revision: Union[str, None] = '20260403_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create rejection_reason_codes table
    op.create_table(
        'rejection_reason_codes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('reason_code', sa.String(length=64), nullable=False),
        sa.Column('reason_name', sa.String(length=128), nullable=False),
        sa.Column('reason_category', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=16), nullable=False, server_default='medium'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reason_code')
    )
    op.create_index('ix_rejection_reason_codes_category', 'rejection_reason_codes', ['reason_category'])
    op.create_index('ix_rejection_reason_codes_active', 'rejection_reason_codes', ['is_active'])

    # Create rejection_reason_stats table
    op.create_table(
        'rejection_reason_stats',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('reason_code', sa.String(length=64), nullable=False),
        sa.Column('stat_date', sa.Date(), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reason_code', 'stat_date', name='uq_rejection_reason_stats_code_date')
    )
    op.create_index('ix_rejection_reason_stats_date', 'rejection_reason_stats', ['stat_date'], postgresql_using='btree')


def downgrade() -> None:
    op.drop_index('ix_rejection_reason_stats_date', table_name='rejection_reason_stats')
    op.drop_table('rejection_reason_stats')
    op.drop_index('ix_rejection_reason_codes_active', table_name='rejection_reason_codes')
    op.drop_index('ix_rejection_reason_codes_category', table_name='rejection_reason_codes')
    op.drop_table('rejection_reason_codes')
