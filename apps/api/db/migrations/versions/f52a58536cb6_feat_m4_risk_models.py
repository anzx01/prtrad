"""feat_m4_risk_models"""

revision = 'f52a58536cb6'
down_revision = '8f9a8414a637'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        'kill_switch_requests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('request_type', sa.String(length=32), nullable=False),
        sa.Column('target_scope', sa.String(length=64), nullable=False),
        sa.Column('requested_by', sa.String(length=128), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('reviewed_by', sa.String(length=128), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_kill_switch_requests')),
    )
    with op.batch_alter_table('kill_switch_requests', schema=None) as batch_op:
        batch_op.create_index('ix_kill_switch_requests_status', ['status'], unique=False)

    op.create_table(
        'risk_exposures',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cluster_code', sa.String(length=64), nullable=False),
        sa.Column('gross_exposure', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('net_exposure', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('position_count', sa.Integer(), nullable=False),
        sa.Column('limit_value', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('utilization_rate', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('is_breached', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_risk_exposures')),
    )
    with op.batch_alter_table('risk_exposures', schema=None) as batch_op:
        batch_op.create_index('ix_risk_exposures_cluster_snapshot', ['cluster_code', 'snapshot_at'], unique=False)

    op.create_table(
        'risk_state_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('from_state', sa.String(length=32), nullable=False),
        sa.Column('to_state', sa.String(length=32), nullable=False),
        sa.Column('trigger_type', sa.String(length=16), nullable=False),
        sa.Column('trigger_metric', sa.String(length=128), nullable=False),
        sa.Column('trigger_value', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('threshold_value', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('actor_id', sa.String(length=128), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_risk_state_events')),
    )
    with op.batch_alter_table('risk_state_events', schema=None) as batch_op:
        batch_op.create_index('ix_risk_state_events_created_at', ['created_at'], unique=False)

    op.create_table(
        'risk_threshold_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cluster_code', sa.String(length=64), nullable=False),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('threshold_value', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_risk_threshold_configs')),
        sa.UniqueConstraint('cluster_code', 'metric_name', name='uq_risk_threshold_cluster_metric'),
    )
    with op.batch_alter_table('risk_threshold_configs', schema=None) as batch_op:
        batch_op.create_index('ix_risk_threshold_configs_active', ['is_active'], unique=False)

    # 清理手动重建时遗留的临时表
    op.execute("DROP TABLE IF EXISTS market_scoring_results_new")


def downgrade() -> None:
    with op.batch_alter_table('risk_threshold_configs', schema=None) as batch_op:
        batch_op.drop_index('ix_risk_threshold_configs_active')
    op.drop_table('risk_threshold_configs')

    with op.batch_alter_table('risk_state_events', schema=None) as batch_op:
        batch_op.drop_index('ix_risk_state_events_created_at')
    op.drop_table('risk_state_events')

    with op.batch_alter_table('risk_exposures', schema=None) as batch_op:
        batch_op.drop_index('ix_risk_exposures_cluster_snapshot')
    op.drop_table('risk_exposures')

    with op.batch_alter_table('kill_switch_requests', schema=None) as batch_op:
        batch_op.drop_index('ix_kill_switch_requests_status')
    op.drop_table('kill_switch_requests')
