from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


UTC = timezone.utc


def _run_alembic_upgrade(repo_root: Path, db_path: Path, revision: str) -> None:
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"

    inline = """
from alembic import command
from alembic.config import Config
from pathlib import Path
import sys

repo_root = Path(sys.argv[1])
db_path = Path(sys.argv[2])
revision = sys.argv[3]
config = Config(str(repo_root / "apps" / "api" / "alembic.ini"))
config.set_main_option("script_location", str(repo_root / "apps" / "api" / "db" / "migrations"))
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
command.upgrade(config, revision)
"""

    subprocess.run(
        [str(venv_python), "-c", inline, str(repo_root), str(db_path), revision],
        check=True,
        cwd=repo_root,
        env={
            **os.environ,
            "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        },
    )


def test_alembic_upgrade_head_supports_inserting_m2_report(tmp_path):
    db_path = tmp_path / "migration-smoke.sqlite3"
    repo_root = Path(__file__).resolve().parents[1]

    _run_alembic_upgrade(repo_root, db_path, "head")

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    try:
        with Session(engine) as session:
            now = datetime.now(UTC).isoformat()
            session.execute(
                text(
                    """
                    INSERT INTO m2_reports (
                        id,
                        report_type,
                        report_period_start,
                        report_period_end,
                        report_data,
                        generated_at,
                        generated_by
                    ) VALUES (
                        :id,
                        :report_type,
                        :report_period_start,
                        :report_period_end,
                        :report_data,
                        :generated_at,
                        :generated_by
                    )
                    """
                ),
                {
                    "id": uuid.uuid4().hex,
                    "report_type": "daily_summary",
                    "report_period_start": now,
                    "report_period_end": now,
                    "report_data": "{}",
                    "generated_at": now,
                    "generated_by": "migration-test",
                },
            )
            session.commit()
            created_at = session.execute(text("SELECT created_at FROM m2_reports")).scalar_one()
            assert created_at is not None
    finally:
        engine.dispose()


def test_alembic_upgrade_head_recovers_sqlite_history_with_failed_m3_artifacts(tmp_path):
    db_path = tmp_path / "migration-history.sqlite3"
    repo_root = Path(__file__).resolve().parents[1]

    _run_alembic_upgrade(repo_root, db_path, "20260404_0010")

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    try:
        with Session(engine) as session:
            created_at = datetime.now(UTC).isoformat()
            session.execute(
                text(
                    """
                    INSERT INTO tag_quality_metrics (
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
                    ) VALUES
                    (:id1, :metric_date1, :rule_version, 10, 8, 1, 1, 0.9, '{}', '{}', :created_at),
                    (:id2, :metric_date2, :rule_version, 11, 9, 1, 1, 0.8, '{}', '{}', :created_at)
                    """
                ),
                {
                    "id1": uuid.uuid4().hex,
                    "id2": uuid.uuid4().hex,
                    "metric_date1": "2026-04-01",
                    "metric_date2": "2026-04-02",
                    "rule_version": "dq_v1",
                    "created_at": created_at,
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO m2_reports (
                        id,
                        report_type,
                        report_period_start,
                        report_period_end,
                        report_data,
                        generated_at,
                        generated_by,
                        created_at
                    ) VALUES
                    (:id1, 'daily_summary', :start1, :end1, '{}', :generated_at, 'seed', :created_at),
                    (:id2, 'daily_summary', :start2, :end2, '{}', :generated_at, 'seed', :created_at)
                    """
                ),
                {
                    "id1": uuid.uuid4().hex,
                    "id2": uuid.uuid4().hex,
                    "start1": "2026-04-01",
                    "start2": "2026-04-02",
                    "end1": "2026-04-05",
                    "end2": "2026-04-05",
                    "generated_at": datetime.now(UTC).isoformat(),
                    "created_at": created_at,
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO rejection_reason_stats (
                        id,
                        reason_code,
                        stat_date,
                        occurrence_count,
                        created_at
                    ) VALUES
                    (:id1, 'LOW_LIQUIDITY', :stat_date1, 2, :created_at),
                    (:id2, 'LOW_LIQUIDITY', :stat_date2, 3, :created_at)
                    """
                ),
                {
                    "id1": uuid.uuid4().hex,
                    "id2": uuid.uuid4().hex,
                    "stat_date1": "2026-04-01",
                    "stat_date2": "2026-04-02",
                    "created_at": created_at,
                },
            )

            # 模拟上一次失败升级留下的半升级残留。
            session.execute(text("CREATE TABLE calibration_units (id TEXT)"))
            session.execute(text("CREATE TABLE netev_candidates (id TEXT)"))
            session.execute(text("CREATE TABLE _alembic_tmp_audit_logs (id TEXT)"))
            session.commit()
    finally:
        engine.dispose()

    _run_alembic_upgrade(repo_root, db_path, "head")

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    try:
        with Session(engine) as session:
            version = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert version == "20260410_0012"

            metric_dates = session.execute(
                text("SELECT metric_date FROM tag_quality_metrics ORDER BY metric_date")
            ).scalars().all()
            report_period_starts = session.execute(
                text("SELECT report_period_start FROM m2_reports ORDER BY report_period_start")
            ).scalars().all()
            stat_dates = session.execute(
                text("SELECT stat_date FROM rejection_reason_stats ORDER BY stat_date")
            ).scalars().all()
            calibration_columns = session.execute(text("PRAGMA table_info(calibration_units)")).fetchall()
            leftover_tmp = session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM sqlite_master
                    WHERE type='table' AND name LIKE '_alembic_tmp_%'
                    """
                )
            ).scalar_one()

            assert metric_dates == ["2026-04-01 00:00:00.000000", "2026-04-02 00:00:00.000000"]
            assert report_period_starts == ["2026-04-01 00:00:00.000000", "2026-04-02 00:00:00.000000"]
            assert stat_dates == ["2026-04-01 00:00:00.000000", "2026-04-02 00:00:00.000000"]
            assert any(column[1] == "price_bucket" for column in calibration_columns)
            assert leftover_tmp == 0
    finally:
        engine.dispose()
