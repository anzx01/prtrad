"""报告生成任务"""
import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func
from celery import Task
from celery.utils.log import get_task_logger
from worker.celery_app import celery_app
from db.models import M2Report, TagQualityMetric, MarketReviewTask
from db.session import session_scope

logger = get_task_logger(__name__)

@celery_app.task(
    name="reports.generate_weekly_report",
    bind=True,
)
def generate_weekly_report(self: Task) -> dict:
    """生成周度报告"""
    logger.info("Generating weekly report")

    now = datetime.now(UTC)
    period_end = now
    period_start = now - timedelta(days=7)

    with session_scope() as session:
        # 1. 检查是否已经存在该周期的报告
        existing = session.scalar(
            select(M2Report).where(
                M2Report.report_type == "weekly_summary",
                M2Report.report_period_start == period_start,
                M2Report.report_period_end == period_end
            )
        )
        if existing:
            return {"status": "skipped", "message": "Report for this period already exists"}

        # 2. 聚合标签质量数据
        metrics = session.scalars(
            select(TagQualityMetric)
            .where(TagQualityMetric.metric_date >= period_start)
            .where(TagQualityMetric.metric_date <= period_end)
        ).all()

        total_classifications = sum(m.total_classifications for m in metrics)
        success_count = sum(m.success_count for m in metrics)

        # 3. 聚合审核队列数据
        review_stats = session.execute(
            select(
                MarketReviewTask.queue_status,
                func.count(MarketReviewTask.id)
            )
            .where(MarketReviewTask.created_at >= period_start)
            .where(MarketReviewTask.created_at <= period_end)
            .group_by(MarketReviewTask.queue_status)
        ).all()

        review_summary = {status: count for status, count in review_stats}

        # 4. 构建报告数据
        report_data = {
            "summary": {
                "total_classifications": total_classifications,
                "overall_success_rate": float(success_count / total_classifications) if total_classifications > 0 else 0.0,
                "metric_records_count": len(metrics)
            },
            "review_queue": review_summary,
            "generated_at": now.isoformat()
        }

        # 5. 创建报告记录
        report = M2Report(
            id=uuid.uuid4(),
            report_type="weekly_summary",
            report_period_start=period_start,
            report_period_end=period_end,
            report_data=report_data,
            generated_at=now,
            generated_by="system"
        )
        session.add(report)

        logger.info(f"Successfully generated weekly report for period {period_start} to {period_end}")
        return {"status": "success", "message": "Weekly report generated", "report_id": str(report.id)}
