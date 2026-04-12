"""feat: M3 calibration and netev models"""

revision = '8f9a8414a637'
down_revision = '20260404_0010'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import Text
from sqlalchemy.dialects import sqlite


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _sqlite_drop_table_if_exists(table_name: str) -> None:
    op.execute(sa.text(f'DROP TABLE IF EXISTS "{table_name}"'))


def _sqlite_cleanup_failed_upgrade_artifacts() -> None:
    bind = op.get_bind()
    tmp_tables = bind.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '_alembic_tmp_%'")
    ).scalars()

    for table_name in tmp_tables:
        _sqlite_drop_table_if_exists(table_name)

    # 旧版本 SQLite 历史库在这次迁移失败后会残留已创建的新表，
    # 重跑 upgrade 前先清理，避免再次被“table already exists”阻塞。
    for table_name in ("calibration_units", "netev_candidates"):
        _sqlite_drop_table_if_exists(table_name)


def _sqlite_datetime_text_expr(column_name: str) -> str:
    raw_value = f'trim(CAST("{column_name}" AS TEXT))'
    return (
        "CASE "
        f'WHEN "{column_name}" IS NULL THEN NULL '
        f"WHEN instr({raw_value}, ' ') > 0 OR instr({raw_value}, 'T') > 0 "
        f"THEN replace({raw_value}, 'T', ' ') "
        f"ELSE substr({raw_value}, 1, 10) || ' 00:00:00.000000' "
        "END"
    )


def _sqlite_date_text_expr(column_name: str) -> str:
    raw_value = f'trim(CAST("{column_name}" AS TEXT))'
    return (
        "CASE "
        f'WHEN "{column_name}" IS NULL THEN NULL '
        f"ELSE substr(replace({raw_value}, 'T', ' '), 1, 10) "
        "END"
    )


def _sqlite_upgrade_tag_quality_metrics() -> None:
    tmp_table = "_alembic_tmp_tag_quality_metrics"
    _sqlite_drop_table_if_exists(tmp_table)

    op.execute(
        sa.text(
            f"""
            CREATE TABLE "{tmp_table}" (
                id CHAR(32) NOT NULL,
                metric_date DATETIME NOT NULL,
                rule_version VARCHAR(64) NOT NULL,
                total_classifications INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                conflict_count INTEGER NOT NULL,
                avg_confidence NUMERIC(8, 4),
                category_distribution JSON NOT NULL,
                bucket_distribution JSON NOT NULL,
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_tag_quality_metrics_date_version UNIQUE (metric_date, rule_version)
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO "{tmp_table}" (
                id,
                metric_date,
                rule_version,
                total_classifications,
                success_count,
                failure_count,
                conflict_count,
                avg_confidence,
                category_distribution,
                bucket_distribution,
                created_at
            )
            SELECT
                id,
                {_sqlite_datetime_text_expr("metric_date")},
                rule_version,
                total_classifications,
                success_count,
                failure_count,
                conflict_count,
                avg_confidence,
                category_distribution,
                bucket_distribution,
                created_at
            FROM tag_quality_metrics
            """
        )
    )
    _sqlite_drop_table_if_exists("tag_quality_metrics")
    op.execute(sa.text(f'ALTER TABLE "{tmp_table}" RENAME TO "tag_quality_metrics"'))
    op.execute(sa.text("CREATE INDEX ix_tag_quality_metrics_date ON tag_quality_metrics (metric_date)"))


def _sqlite_upgrade_m2_reports() -> None:
    tmp_table = "_alembic_tmp_m2_reports"
    _sqlite_drop_table_if_exists(tmp_table)

    op.execute(
        sa.text(
            f"""
            CREATE TABLE "{tmp_table}" (
                id CHAR(32) NOT NULL,
                report_type VARCHAR(32) NOT NULL,
                report_period_start DATETIME NOT NULL,
                report_period_end DATETIME NOT NULL,
                report_data JSON NOT NULL,
                generated_at DATETIME NOT NULL,
                generated_by VARCHAR(128),
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_m2_reports_type_period
                    UNIQUE (report_type, report_period_start, report_period_end)
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO "{tmp_table}" (
                id,
                report_type,
                report_period_start,
                report_period_end,
                report_data,
                generated_at,
                generated_by,
                created_at
            )
            SELECT
                id,
                report_type,
                {_sqlite_datetime_text_expr("report_period_start")},
                {_sqlite_datetime_text_expr("report_period_end")},
                report_data,
                generated_at,
                generated_by,
                created_at
            FROM m2_reports
            """
        )
    )
    _sqlite_drop_table_if_exists("m2_reports")
    op.execute(sa.text(f'ALTER TABLE "{tmp_table}" RENAME TO "m2_reports"'))
    op.execute(sa.text("CREATE INDEX ix_m2_reports_type_period ON m2_reports (report_type, report_period_end)"))


def _sqlite_upgrade_rejection_reason_stats() -> None:
    tmp_table = "_alembic_tmp_rejection_reason_stats"
    _sqlite_drop_table_if_exists(tmp_table)

    op.execute(
        sa.text(
            f"""
            CREATE TABLE "{tmp_table}" (
                id CHAR(32) NOT NULL,
                reason_code VARCHAR(64) NOT NULL,
                stat_date DATETIME NOT NULL,
                occurrence_count INTEGER DEFAULT '0' NOT NULL,
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_rejection_reason_stats_code_date UNIQUE (reason_code, stat_date)
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO "{tmp_table}" (
                id,
                reason_code,
                stat_date,
                occurrence_count,
                created_at
            )
            SELECT
                id,
                reason_code,
                {_sqlite_datetime_text_expr("stat_date")},
                occurrence_count,
                created_at
            FROM rejection_reason_stats
            """
        )
    )
    _sqlite_drop_table_if_exists("rejection_reason_stats")
    op.execute(sa.text(f'ALTER TABLE "{tmp_table}" RENAME TO "rejection_reason_stats"'))
    op.execute(sa.text("CREATE INDEX ix_rejection_reason_stats_date ON rejection_reason_stats (stat_date)"))


def _sqlite_downgrade_tag_quality_metrics() -> None:
    tmp_table = "_alembic_tmp_tag_quality_metrics"
    _sqlite_drop_table_if_exists(tmp_table)

    op.execute(
        sa.text(
            f"""
            CREATE TABLE "{tmp_table}" (
                id CHAR(32) NOT NULL,
                metric_date DATE NOT NULL,
                rule_version VARCHAR(64) NOT NULL,
                total_classifications INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                conflict_count INTEGER NOT NULL,
                avg_confidence NUMERIC(8, 4),
                category_distribution JSON NOT NULL,
                bucket_distribution JSON NOT NULL,
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_tag_quality_metrics_date_version UNIQUE (metric_date, rule_version)
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO "{tmp_table}" (
                id,
                metric_date,
                rule_version,
                total_classifications,
                success_count,
                failure_count,
                conflict_count,
                avg_confidence,
                category_distribution,
                bucket_distribution,
                created_at
            )
            SELECT
                id,
                {_sqlite_date_text_expr("metric_date")},
                rule_version,
                total_classifications,
                success_count,
                failure_count,
                conflict_count,
                avg_confidence,
                category_distribution,
                bucket_distribution,
                created_at
            FROM tag_quality_metrics
            """
        )
    )
    _sqlite_drop_table_if_exists("tag_quality_metrics")
    op.execute(sa.text(f'ALTER TABLE "{tmp_table}" RENAME TO "tag_quality_metrics"'))
    op.execute(sa.text("CREATE INDEX ix_tag_quality_metrics_date ON tag_quality_metrics (metric_date)"))


def _sqlite_downgrade_m2_reports() -> None:
    tmp_table = "_alembic_tmp_m2_reports"
    _sqlite_drop_table_if_exists(tmp_table)

    op.execute(
        sa.text(
            f"""
            CREATE TABLE "{tmp_table}" (
                id CHAR(32) NOT NULL,
                report_type VARCHAR(32) NOT NULL,
                report_period_start DATE NOT NULL,
                report_period_end DATE NOT NULL,
                report_data JSON NOT NULL,
                generated_at DATETIME NOT NULL,
                generated_by VARCHAR(128),
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_m2_reports_type_period
                    UNIQUE (report_type, report_period_start, report_period_end)
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO "{tmp_table}" (
                id,
                report_type,
                report_period_start,
                report_period_end,
                report_data,
                generated_at,
                generated_by,
                created_at
            )
            SELECT
                id,
                report_type,
                {_sqlite_date_text_expr("report_period_start")},
                {_sqlite_date_text_expr("report_period_end")},
                report_data,
                generated_at,
                generated_by,
                created_at
            FROM m2_reports
            """
        )
    )
    _sqlite_drop_table_if_exists("m2_reports")
    op.execute(sa.text(f'ALTER TABLE "{tmp_table}" RENAME TO "m2_reports"'))
    op.execute(sa.text("CREATE INDEX ix_m2_reports_type_period ON m2_reports (report_type, report_period_end)"))


def _sqlite_downgrade_rejection_reason_stats() -> None:
    tmp_table = "_alembic_tmp_rejection_reason_stats"
    _sqlite_drop_table_if_exists(tmp_table)

    op.execute(
        sa.text(
            f"""
            CREATE TABLE "{tmp_table}" (
                id CHAR(32) NOT NULL,
                reason_code VARCHAR(64) NOT NULL,
                stat_date DATE NOT NULL,
                occurrence_count INTEGER DEFAULT '0' NOT NULL,
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_rejection_reason_stats_code_date UNIQUE (reason_code, stat_date)
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO "{tmp_table}" (
                id,
                reason_code,
                stat_date,
                occurrence_count,
                created_at
            )
            SELECT
                id,
                reason_code,
                {_sqlite_date_text_expr("stat_date")},
                occurrence_count,
                created_at
            FROM rejection_reason_stats
            """
        )
    )
    _sqlite_drop_table_if_exists("rejection_reason_stats")
    op.execute(sa.text(f'ALTER TABLE "{tmp_table}" RENAME TO "rejection_reason_stats"'))
    op.execute(sa.text("CREATE INDEX ix_rejection_reason_stats_date ON rejection_reason_stats (stat_date)"))


def upgrade() -> None:
    if _is_sqlite():
        _sqlite_cleanup_failed_upgrade_artifacts()

    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('calibration_units',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('price_bucket', sa.String(length=32), nullable=False),
    sa.Column('category_code', sa.String(length=64), nullable=False),
    sa.Column('time_bucket', sa.String(length=32), nullable=False),
    sa.Column('liquidity_tier', sa.String(length=32), nullable=False),
    sa.Column('window_type', sa.String(length=32), nullable=False),
    sa.Column('sample_count', sa.Integer(), nullable=False),
    sa.Column('edge_estimate', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('interval_low', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('interval_high', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('disabled_reason', sa.String(length=128), nullable=True),
    sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_calibration_units')),
    sa.UniqueConstraint('price_bucket', 'category_code', 'time_bucket', 'liquidity_tier', 'window_type', name='uq_calibration_units_key')
    )
    op.create_index('ix_calibration_units_active', 'calibration_units', ['is_active'], unique=False)
    op.create_table('netev_candidates',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('market_ref_id', sa.Uuid(), nullable=False),
    sa.Column('calibration_unit_id', sa.Uuid(), nullable=True),
    sa.Column('gross_edge', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('fee_cost', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('slippage_cost', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('dispute_discount', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('net_ev', sa.Numeric(precision=12, scale=6), nullable=False),
    sa.Column('admission_decision', sa.String(length=32), nullable=False),
    sa.Column('rejection_reason_code', sa.String(length=64), nullable=True),
    sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['calibration_unit_id'], ['calibration_units.id'], name=op.f('fk_netev_candidates_calibration_unit_id_calibration_units'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['market_ref_id'], ['markets.id'], name=op.f('fk_netev_candidates_market_ref_id_markets'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_netev_candidates'))
    )
    op.create_index('ix_netev_candidates_market_decision', 'netev_candidates', ['market_ref_id', 'admission_decision'], unique=False)

    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    with op.batch_alter_table('data_quality_results', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    with op.batch_alter_table('decision_logs', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=True)

    if _is_sqlite():
        _sqlite_upgrade_m2_reports()
    else:
        with op.batch_alter_table('m2_reports', schema=None) as batch_op:
            batch_op.alter_column('report_period_start',
                   existing_type=sa.DATE(),
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=False)
            batch_op.alter_column('report_period_end',
                   existing_type=sa.DATE(),
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=False)

    with op.batch_alter_table('market_classification_results', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    with op.batch_alter_table('market_review_tasks', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('classification_result_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    with op.batch_alter_table('market_snapshots', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    with op.batch_alter_table('market_tag_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assignment_entry_metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), 'postgresql'), nullable=True))
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('classification_result_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.drop_column('assignment_metadata')

    with op.batch_alter_table('market_tag_explanations', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('classification_result_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    with op.batch_alter_table('markets', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.drop_constraint(batch_op.f('uq_markets_market_id'), type_='unique')
        batch_op.drop_index(batch_op.f('ix_markets_market_id'))
        batch_op.create_index(batch_op.f('ix_markets_market_id'), ['market_id'], unique=True)

    with op.batch_alter_table('rejection_reason_codes', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_rejection_reason_codes_reason_code'), type_='unique')
        batch_op.create_index(batch_op.f('ix_rejection_reason_codes_reason_category'), ['reason_category'], unique=False)
        batch_op.create_index(batch_op.f('ix_rejection_reason_codes_reason_code'), ['reason_code'], unique=True)

    if _is_sqlite():
        _sqlite_upgrade_rejection_reason_stats()
    else:
        with op.batch_alter_table('rejection_reason_stats', schema=None) as batch_op:
            batch_op.alter_column('stat_date',
                   existing_type=sa.DATE(),
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=False)

    with op.batch_alter_table('tag_dictionary_entries', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    if _is_sqlite():
        _sqlite_upgrade_tag_quality_metrics()
    else:
        with op.batch_alter_table('tag_quality_metrics', schema=None) as batch_op:
            batch_op.alter_column('metric_date',
                   existing_type=sa.DATE(),
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=False)

    with op.batch_alter_table('tag_rule_versions', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('base_version_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=True)
        batch_op.alter_column('supersedes_version_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=True)

    with op.batch_alter_table('tag_rules', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)
        batch_op.alter_column('rule_version_id',
               existing_type=sa.NUMERIC(),
               type_=sa.Uuid(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tag_rules', schema=None) as batch_op:
        batch_op.alter_column('rule_version_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    with op.batch_alter_table('tag_rule_versions', schema=None) as batch_op:
        batch_op.alter_column('supersedes_version_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
        batch_op.alter_column('base_version_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    if _is_sqlite():
        _sqlite_downgrade_tag_quality_metrics()
    else:
        with op.batch_alter_table('tag_quality_metrics', schema=None) as batch_op:
            batch_op.alter_column('metric_date',
                   existing_type=sa.DateTime(timezone=True),
                   type_=sa.DATE(),
                   existing_nullable=False)

    with op.batch_alter_table('tag_dictionary_entries', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    if _is_sqlite():
        _sqlite_downgrade_rejection_reason_stats()
    else:
        with op.batch_alter_table('rejection_reason_stats', schema=None) as batch_op:
            batch_op.alter_column('stat_date',
                   existing_type=sa.DateTime(timezone=True),
                   type_=sa.DATE(),
                   existing_nullable=False)

    with op.batch_alter_table('rejection_reason_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rejection_reason_codes_reason_code'))
        batch_op.drop_index(batch_op.f('ix_rejection_reason_codes_reason_category'))
        batch_op.create_unique_constraint(batch_op.f('uq_rejection_reason_codes_reason_code'), ['reason_code'])

    with op.batch_alter_table('markets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_markets_market_id'))
        batch_op.create_index(batch_op.f('ix_markets_market_id'), ['market_id'], unique=False)
        batch_op.create_unique_constraint(batch_op.f('uq_markets_market_id'), ['market_id'])
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    with op.batch_alter_table('market_tag_explanations', schema=None) as batch_op:
        batch_op.alter_column('market_ref_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('classification_result_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    with op.batch_alter_table('market_tag_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assignment_metadata', sqlite.JSON(), nullable=True))
        batch_op.alter_column('market_ref_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('classification_result_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.drop_column('assignment_entry_metadata')

    with op.batch_alter_table('market_snapshots', schema=None) as batch_op:
        batch_op.alter_column('market_ref_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    with op.batch_alter_table('market_review_tasks', schema=None) as batch_op:
        batch_op.alter_column('classification_result_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('market_ref_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    with op.batch_alter_table('market_classification_results', schema=None) as batch_op:
        batch_op.alter_column('market_ref_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    if _is_sqlite():
        _sqlite_downgrade_m2_reports()
    else:
        with op.batch_alter_table('m2_reports', schema=None) as batch_op:
            batch_op.alter_column('report_period_end',
                   existing_type=sa.DateTime(timezone=True),
                   type_=sa.DATE(),
                   existing_nullable=False)
            batch_op.alter_column('report_period_start',
                   existing_type=sa.DateTime(timezone=True),
                   type_=sa.DATE(),
                   existing_nullable=False)

    with op.batch_alter_table('decision_logs', schema=None) as batch_op:
        batch_op.alter_column('market_ref_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    with op.batch_alter_table('data_quality_results', schema=None) as batch_op:
        batch_op.alter_column('market_ref_id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.Uuid(),
               type_=sa.NUMERIC(),
               existing_nullable=False)

    # ### end Alembic commands ###
