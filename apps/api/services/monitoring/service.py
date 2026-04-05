"""监控服务"""
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from db.models import AuditLog, MarketReviewTask, TagQualityMetric, TagQualityAnomaly

class MonitoringService:
    def __init__(self, db: Session):
        self.db = db

    def get_metrics(self):
        """获取系统监控指标"""
        # 1. 审核队列统计
        review_stats = self.db.execute(
            select(
                MarketReviewTask.queue_status,
                func.count(MarketReviewTask.id)
            ).group_by(MarketReviewTask.queue_status)
        ).all()

        queue_metrics = {status: count for status, count in review_stats}

        # 今日审核完成统计
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        approved_today = self.db.scalar(
            select(func.count(MarketReviewTask.id))
            .where(MarketReviewTask.queue_status == "approved")
            .where(MarketReviewTask.resolved_at >= today_start)
        ) or 0

        rejected_today = self.db.scalar(
            select(func.count(MarketReviewTask.id))
            .where(MarketReviewTask.queue_status == "rejected")
            .where(MarketReviewTask.resolved_at >= today_start)
        ) or 0

        # 2. 标签质量指标 (取最新一条)
        latest_quality = self.db.scalar(
            select(TagQualityMetric).order_by(TagQualityMetric.metric_date.desc()).limit(1)
        )

        quality_metrics = {
            "latest_total": latest_quality.total_classifications if latest_quality else 0,
            "latest_success_rate": float(latest_quality.success_count / latest_quality.total_classifications) if latest_quality and latest_quality.total_classifications > 0 else 0.0,
            "latest_avg_confidence": float(latest_quality.avg_confidence) if latest_quality and latest_quality.avg_confidence else 0.0,
        }

        # 未解决异常数
        open_anomalies = self.db.scalar(
            select(func.count(TagQualityAnomaly.id)).where(TagQualityAnomaly.is_resolved == False)
        ) or 0

        # 3. 数据质量 (AuditLog 最近 24h 失败事件)
        one_day_ago = datetime.now(UTC) - timedelta(days=1)
        recent_failures = self.db.scalar(
            select(func.count(AuditLog.id))
            .where(AuditLog.result == "failure")
            .where(AuditLog.created_at >= one_day_ago)
        ) or 0

        return {
            "status": "ok",
            "metrics": {
                "review_queue": {
                    "pending": queue_metrics.get("pending", 0),
                    "in_progress": queue_metrics.get("in_progress", 0),
                    "approved_today": approved_today,
                    "rejected_today": rejected_today
                },
                "tag_quality": {
                    **quality_metrics,
                    "open_anomalies": open_anomalies
                },
                "dq": {
                    "recent_failures": recent_failures
                }
            }
        }
