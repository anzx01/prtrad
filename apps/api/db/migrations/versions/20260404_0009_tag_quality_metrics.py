"""tag quality metrics tables

Revision ID: 20260404_0009
Revises: 20260404_0008
Create Date: 2026-04-04 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260404_0009'
down_revision: Union[str, None] = '20260404_0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tag_quality_metrics table
    op.create_table(
        'tag_quality_metrics',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('metric_date', sa.Date(), nullable=False),
        sa.Column('rule_version', sa.String(length=64), nullable=False),
        sa.Column('total_classifications', sa.Integer(), nullable=False),
        sa.Column('success_count', sa.Integer(), nullable=False),
        sa.Column('failure_count', sa.Integer(), nullable=False),
        sa.Column('conflict_count', sa.Integer(), nullable=False),
        sa.Column('avg_confidence', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('category_distribution', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('bucket_distribution', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('metric_date', 'rule_version', name='uq_tag_quality_metrics_date_version')
    )
    op.create_index('ix_tag_quality_metrics_date', 'tag_quality_metrics', ['metric_date'], postgresql_using='btree')

    # Create tag_quality_anomalies table
    op.create_table(
        'tag_quality_anomalies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('anomaly_type', sa.String(length=32), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rule_version', sa.String(length=64), nullable=True),
        sa.Column('anomaly_details', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tag_quality_anomalies_type_severity', 'tag_quality_anomalies', ['anomaly_type', 'severity'])
    op.create_index('ix_tag_quality_anomalies_detected_at', 'tag_quality_anomalies', ['detected_at'], postgresql_using='btree')


def downgrade() -> None:
    op.drop_index('ix_tag_quality_anomalies_detected_at', table_name='tag_quality_anomalies')
    op.drop_index('ix_tag_quality_anomalies_type_severity', table_name='tag_quality_anomalies')
    op.drop_table('tag_quality_anomalies')
    op.drop_index('ix_tag_quality_metrics_date', table_name='tag_quality_metrics')
    op.drop_table('tag_quality_metrics')
