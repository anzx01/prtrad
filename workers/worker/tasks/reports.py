"""报告生成任务。"""
from __future__ import annotations

from celery import Task
from celery.utils.log import get_task_logger

from db.session import session_scope
from services.reports import ReportService
from worker.celery_app import celery_app


logger = get_task_logger(__name__)


def _generate_report(*, report_type: str, generated_by: str = "system", stage_name: str | None = None) -> dict:
    with session_scope() as session:
        service = ReportService(session)
        report = service.generate_report(
            report_type=report_type,
            generated_by=generated_by,
            stage_name=stage_name,
        )
        payload = service.serialize_report(report)
        logger.info("report generated", extra={"report_type": report_type, "report_id": payload["id"]})
        return {
            "status": "success",
            "report_type": report_type,
            "report_id": payload["id"],
        }


@celery_app.task(name="reports.generate_daily_summary", bind=True)
def generate_daily_summary(self: Task) -> dict:
    """生成日报。"""
    logger.info("Generating daily summary report")
    return _generate_report(report_type="daily_summary")


@celery_app.task(name="reports.generate_weekly_report", bind=True)
def generate_weekly_report(self: Task) -> dict:
    """生成周报。"""
    logger.info("Generating weekly summary report")
    return _generate_report(report_type="weekly_summary")


@celery_app.task(name="reports.generate_stage_review", bind=True)
def generate_stage_review(self: Task, stage_name: str = "M6") -> dict:
    """生成阶段评审报告。"""
    logger.info("Generating stage review report", extra={"stage_name": stage_name})
    return _generate_report(report_type="stage_review", stage_name=stage_name)
