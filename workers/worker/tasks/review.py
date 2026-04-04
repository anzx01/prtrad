"""
审核任务管理

自动生成和管理审核任务队列
"""

from datetime import UTC, datetime

from celery import Task
from celery.utils.log import get_task_logger

from worker.celery_app import celery_app
from worker.tasks.base import AuditedTask

logger = get_task_logger(__name__)


@celery_app.task(
    name="review.generate_review_tasks",
    base=AuditedTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_review_tasks(
    self: Task,
    *,
    market_limit: int | None = None,
) -> dict:
    """
    为需要审核的分类结果生成审核任务

    Args:
        market_limit: 限制处理的市场数量（None 表示使用配置默认值）

    Returns:
        审核任务生成统计信息
    """
    from db.models import MarketClassificationResult, MarketReviewTask
    from db.session import session_scope
    from services.review import ReviewService, ReviewTaskInput
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    generated_at = datetime.now(UTC)

    try:
        with session_scope() as session:
            # 查询需要审核但尚未创建审核任务的分类结果
            stmt = (
                select(MarketClassificationResult)
                .outerjoin(MarketClassificationResult.review_task)
                .where(
                    MarketClassificationResult.requires_review == True,  # noqa: E712
                    MarketReviewTask.id.is_(None),  # 尚未创建审核任务
                )
                .options(selectinload(MarketClassificationResult.market))
                .order_by(MarketClassificationResult.classified_at.desc())
            )

            if market_limit:
                stmt = stmt.limit(market_limit)

            classification_results = list(session.scalars(stmt).all())

            if not classification_results:
                logger.info("No classification results requiring review")
                return {
                    "status": "success",
                    "generated_at": generated_at.isoformat(),
                    "total": 0,
                    "created": 0,
                }

            # 创建审计服务
            from services.audit import AuditLogService

            audit_service = AuditLogService()

            # 创建审核服务
            review_service = ReviewService(
                db=session,
                audit_service=audit_service,
                task_id=self.request.id,
            )

            created_count = 0
            failed_count = 0

            for classification_result in classification_results:
                try:
                    # 确定审核原因码
                    review_reason_code = classification_result.failure_reason_code
                    if not review_reason_code:
                        if classification_result.conflict_count > 0:
                            review_reason_code = "CONFLICT_DETECTED"
                        elif classification_result.confidence and classification_result.confidence < 0.7:
                            review_reason_code = "LOW_CONFIDENCE"
                        else:
                            review_reason_code = "MANUAL_REVIEW_REQUIRED"

                    # 确定优先级
                    priority = "normal"
                    if classification_result.conflict_count > 2:
                        priority = "high"
                    elif classification_result.confidence and classification_result.confidence < 0.5:
                        priority = "high"

                    # 创建审核任务
                    review_input = ReviewTaskInput(
                        market_ref_id=classification_result.market_ref_id,
                        classification_result_id=classification_result.id,
                        review_reason_code=review_reason_code,
                        priority=priority,
                        review_payload={
                            "classification_status": classification_result.classification_status,
                            "primary_category_code": classification_result.primary_category_code,
                            "confidence": float(classification_result.confidence) if classification_result.confidence else None,
                            "conflict_count": classification_result.conflict_count,
                            "generated_at": generated_at.isoformat(),
                        },
                    )

                    review_service.create_review_task(review_input)
                    created_count += 1

                except Exception as exc:
                    logger.error(
                        f"Failed to create review task for classification {classification_result.id}: {exc}",
                        exc_info=True,
                    )
                    failed_count += 1

            session.commit()

            logger.info(
                f"Review task generation completed: {created_count}/{len(classification_results)} tasks created, "
                f"{failed_count} failed"
            )

            return {
                "status": "success",
                "generated_at": generated_at.isoformat(),
                "total": len(classification_results),
                "created": created_count,
                "failed": failed_count,
            }

    except Exception as exc:
        logger.error(f"Review task generation failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
