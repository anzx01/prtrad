"""
市场评分任务

对已分类的市场进行清晰度和客观性评分
"""

from datetime import UTC, datetime

from celery import Task
from celery.utils.log import get_task_logger

from worker.celery_app import celery_app
from worker.tasks.base import AuditedTask

logger = get_task_logger(__name__)


@celery_app.task(
    name="scoring.score_classified_markets",
    base=AuditedTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def score_classified_markets(
    self: Task,
    *,
    market_limit: int | None = None,
) -> dict:
    """
    对已分类的市场进行评分

    Args:
        market_limit: 限制处理的市场数量（None 表示使用配置默认值）

    Returns:
        评分统计信息
    """
    from db.models import MarketClassificationResult
    from db.session import session_scope
    from services.scoring import ScoringService
    from services.scoring.contracts import ScoringThresholds
    from sqlalchemy import select

    scored_at = datetime.now(UTC)

    try:
        with session_scope() as session:
            # 查询最近的分类结果（尚未评分的）
            stmt = (
                select(MarketClassificationResult)
                .outerjoin(
                    MarketClassificationResult.scoring_results  # type: ignore
                )
                .where(MarketClassificationResult.classification_status == "Tagged")
                .order_by(MarketClassificationResult.classified_at.desc())
            )

            if market_limit:
                stmt = stmt.limit(market_limit)

            classification_results = session.scalars(stmt).all()

            if not classification_results:
                logger.info("No classification results to score")
                return {
                    "status": "success",
                    "scored_at": scored_at.isoformat(),
                    "total": 0,
                    "scored": 0,
                }

            # 创建审计服务
            from services.audit import AuditLogService

            audit_service = AuditLogService()

            # 创建评分服务
            scoring_service = ScoringService(
                db=session,
                thresholds=ScoringThresholds(),
                audit_service=audit_service,
                task_id=self.request.id,
            )

            # 执行评分
            stats = scoring_service.score_and_persist_classification_results(
                classification_results=classification_results,
                classified_at=scored_at,
            )

            session.commit()

            logger.info(
                f"Scoring completed: {stats['scored']}/{stats['total']} markets scored, "
                f"{stats['approved']} approved, {stats['review_required']} need review, "
                f"{stats['rejected']} rejected"
            )

            return {
                "status": "success",
                "scored_at": scored_at.isoformat(),
                **stats,
            }

    except Exception as exc:
        logger.error(f"Scoring task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
