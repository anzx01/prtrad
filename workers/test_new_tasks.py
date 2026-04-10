#!/usr/bin/env python
"""
独立烟测 Worker 任务入口。

用途：
- 验证任务模块可导入
- 验证任务函数可执行
- 不依赖 Celery worker 常驻进程
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKERS_DIR = ROOT / "workers"
API_DIR = ROOT / "apps" / "api"


def _bootstrap_paths() -> None:
    for path in (WORKERS_DIR, API_DIR):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _print_header(title: str) -> None:
    print(title)
    print("-" * 40)


def main() -> None:
    _bootstrap_paths()

    print("=== Testing Worker Tasks ===")
    print("")

    print("[Test 1] Tag Quality Tasks")
    _print_header("")
    try:
        from worker.tasks.tag_quality import daily_metrics_aggregation, detect_anomalies

        print(f"[OK] daily_metrics_aggregation: {daily_metrics_aggregation.name}")
        print(f"[OK] detect_anomalies: {detect_anomalies.name}")
        print(f"[OK] Execution result: {daily_metrics_aggregation()}")
        print(f"[OK] Execution result: {detect_anomalies()}")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        raise

    print("")
    print("[Test 2] Monitoring Tasks")
    _print_header("")
    try:
        from worker.tasks.monitoring import aggregate_metrics

        print(f"[OK] aggregate_metrics: {aggregate_metrics.name}")
        print(f"[OK] Execution result: {aggregate_metrics()}")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        raise

    print("")
    print("[Test 3] Reports Tasks")
    _print_header("")
    try:
        from worker.tasks.reports import (
            generate_daily_summary,
            generate_stage_review,
            generate_weekly_report,
        )

        print(f"[OK] generate_daily_summary: {generate_daily_summary.name}")
        print(f"[OK] generate_weekly_report: {generate_weekly_report.name}")
        print(f"[OK] generate_stage_review: {generate_stage_review.name}")
        print(f"[OK] Daily execution result: {generate_daily_summary()}")
        print(f"[OK] Weekly execution result: {generate_weekly_report()}")
        print(f"[OK] Stage execution result: {generate_stage_review(stage_name='M6')}")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        raise

    print("")
    print("=" * 40)
    print("Summary:")
    print("  [OK] 3 task modules")
    print("  [OK] 6 tasks total")
    print("  [OK] All tasks can be imported")
    print("  [OK] All tasks can be executed")
    print("")
    print("Worker Tasks Test: PASSED")
    print("=" * 40)


if __name__ == "__main__":
    main()
