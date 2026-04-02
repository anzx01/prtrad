from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ScoringInput:
    """评分输入数据"""

    market_ref_id: UUID
    question: str
    description: str | None
    resolution_criteria: str | None
    primary_category_code: str | None
    admission_bucket_code: str | None
    classification_confidence: float | None


@dataclass
class ScoringResult:
    """评分结果"""

    market_ref_id: UUID
    clarity_score: float
    resolution_objectivity_score: float
    overall_score: float
    admission_recommendation: str  # "Approved", "ReviewRequired", "Rejected"
    rejection_reason_code: str | None
    scoring_details: dict
    scored_at: datetime


@dataclass
class ScoringThresholds:
    """评分阈值配置"""

    clarity_min_approved: float = 0.7
    clarity_min_review: float = 0.5
    objectivity_min_approved: float = 0.7
    objectivity_min_review: float = 0.5
    overall_min_approved: float = 0.7
    overall_min_review: float = 0.5
