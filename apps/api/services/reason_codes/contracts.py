"""
拒绝原因码服务契约
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ReasonCodeInput:
    """原因码创建输入"""

    reason_code: str
    reason_name: str
    reason_category: str  # 'classification', 'scoring', 'review'
    description: str | None = None
    severity: str = "medium"  # 'low', 'medium', 'high', 'critical'
    sort_order: int = 100


@dataclass
class ReasonCodeUpdate:
    """原因码更新输入"""

    reason_name: str | None = None
    description: str | None = None
    severity: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
