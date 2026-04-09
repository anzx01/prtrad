"""Monitoring service."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import AuditLog, MarketReviewTask, TagQualityAnomaly, TagQualityMetric
from services.review.service import normalize_review_status


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db

    def get_metrics(self):
        review_stats = self.db.execute(
            select(
                MarketReviewTask.queue_status,
                func.count(MarketReviewTask.id),
            ).group_by(MarketReviewTask.queue_status)
        ).all()

        queue_metrics: dict[str, int] = {}
        for status, count in review_stats:
            normalized_status = normalize_review_status(status) or status
            queue_metrics[normalized_status] = queue_metrics.get(normalized_status, 0) + count

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

        latest_quality = self.db.scalar(
            select(TagQualityMetric).order_by(TagQualityMetric.metric_date.desc()).limit(1)
        )

        quality_metrics = {
            "latest_total": latest_quality.total_classifications if latest_quality else 0,
            "latest_success_rate": float(latest_quality.success_count / latest_quality.total_classifications)
            if latest_quality and latest_quality.total_classifications > 0
            else 0.0,
            "latest_avg_confidence": float(latest_quality.avg_confidence)
            if latest_quality and latest_quality.avg_confidence
            else 0.0,
        }

        open_anomalies = self.db.scalar(
            select(func.count(TagQualityAnomaly.id)).where(TagQualityAnomaly.is_resolved == False)
        ) or 0

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
                    "rejected_today": rejected_today,
                },
                "tag_quality": {
                    **quality_metrics,
                    "open_anomalies": open_anomalies,
                },
                "dq": {
                    "recent_failures": recent_failures,
                },
            },
        }
