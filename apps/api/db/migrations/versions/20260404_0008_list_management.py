"""list management tables

Revision ID: 20260404_0008
Revises: 20260404_0007
Create Date: 2026-04-04 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260404_0008'
down_revision: Union[str, None] = '20260404_0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create list_entries table
    op.create_table(
        'list_entries',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('list_type', sa.String(length=16), nullable=False),
        sa.Column('entry_type', sa.String(length=32), nullable=False),
        sa.Column('entry_value', sa.Text(), nullable=False),
        sa.Column('match_mode', sa.String(length=16), nullable=False, server_default='exact'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('added_by', sa.String(length=128), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('entry_metadata', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_list_entries_type_active', 'list_entries', ['list_type', 'is_active'])
    op.create_index('ix_list_entries_entry_type', 'list_entries', ['entry_type'])
    op.create_index('ix_list_entries_expires_at', 'list_entries', ['expires_at'], postgresql_where=sa.text('expires_at IS NOT NULL'))

    # Create list_versions table
    op.create_table(
        'list_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('version_code', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=False),
        sa.Column('snapshot_payload', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_code')
    )
    op.create_index('ix_list_versions_status', 'list_versions', ['status'])


def downgrade() -> None:
    op.drop_index('ix_list_versions_status', table_name='list_versions')
    op.drop_table('list_versions')
    op.drop_index('ix_list_entries_expires_at', table_name='list_entries')
    op.drop_index('ix_list_entries_entry_type', table_name='list_entries')
    op.drop_index('ix_list_entries_type_active', table_name='list_entries')
    op.drop_table('list_entries')
