"""标签质量服务"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from db.models import TagQualityMetric, TagQualityAnomaly

class TagQualityService:
    def __init__(self, db: Session):
        self.db = db

    def get_metrics(self):
        """获取最近 7 次标签质量指标"""
        metrics = self.db.scalars(
            select(TagQualityMetric)
            .order_by(TagQualityMetric.metric_date.desc())
            .limit(7)
        ).all()

        # 获取未解决的异常统计
        anomaly_stats = self.db.execute(
            select(
                TagQualityAnomaly.severity,
                func.count(TagQualityAnomaly.id)
            )
            .where(TagQualityAnomaly.is_resolved == False)
            .group_by(TagQualityAnomaly.severity)
        ).all()

        anomalies_summary = {severity: count for severity, count in anomaly_stats}

        return [
            {
                "metric_date": m.metric_date.isoformat(),
                "rule_version": m.rule_version,
                "total_classifications": m.total_classifications,
                "success_rate": float(m.success_count / m.total_classifications) if m.total_classifications > 0 else 0.0,
                "avg_confidence": float(m.avg_confidence) if m.avg_confidence else 0.0,
                "conflict_count": m.conflict_count,
                "category_distribution": m.category_distribution,
                "anomalies_summary": anomalies_summary if i == 0 else None  # 仅在最新一条中附加异常摘要
            }
            for i, m in enumerate(metrics)
        ]
