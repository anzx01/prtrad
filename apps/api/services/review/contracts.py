"""
审核任务服务契约定义

定义审核任务流的输入输出数据结构。
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ReviewTaskInput:
    """审核任务创建输入"""

    market_ref_id: UUID
    classification_result_id: UUID
    review_reason_code: str | None = None
    priority: str = "normal"  # low, normal, high, urgent
    review_payload: dict | None = None


@dataclass
class ReviewTaskUpdate:
    """审核任务更新输入"""

    queue_status: str | None = None  # pending, in_progress, approved, rejected, cancelled
    assigned_to: str | None = None
    review_payload: dict | None = None
