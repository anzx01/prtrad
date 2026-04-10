from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


UTC = timezone.utc


def test_alembic_upgrade_head_supports_inserting_m2_report(tmp_path):
    db_path = tmp_path / "migration-smoke.sqlite3"
    repo_root = Path(__file__).resolve().parents[1]
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"

    inline = """
from alembic import command
from alembic.config import Config
from pathlib import Path
import sys

repo_root = Path(sys.argv[1])
db_path = Path(sys.argv[2])
config = Config(str(repo_root / "apps" / "api" / "alembic.ini"))
config.set_main_option("script_location", str(repo_root / "apps" / "api" / "db" / "migrations"))
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
command.upgrade(config, "head")
"""

    subprocess.run(
        [str(venv_python), "-c", inline, str(repo_root), str(db_path)],
        check=True,
        cwd=repo_root,
        env={
            **os.environ,
            "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
        },
    )

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
