import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from .contracts import ScoringInput, ScoringResult, ScoringThresholds


class ScoringService:
    """
    清晰度与客观性评分服务

    根据市场的问题、描述、结算标准等文本内容，计算：
    1. clarity_score: 问题清晰度评分
    2. resolution_objectivity_score: 结算客观性评分
    3. overall_score: 综合评分

    并根据阈值给出准入建议。
    """

    def __init__(
        self,
        db: Session,
        thresholds: ScoringThresholds | None = None,
        audit_service=None,
        task_id: str | None = None,
    ):
        self.db = db
        self.thresholds = thresholds or ScoringThresholds()
        self.audit_service = audit_service
        self.task_id = task_id

    def score_market(self, scoring_input: ScoringInput) -> ScoringResult:
        """
        对单个市场进行评分

        Args:
            scoring_input: 评分输入数据

        Returns:
            ScoringResult: 评分结果
        """
        # 计算清晰度评分
        clarity_score, clarity_details = self._calculate_clarity_score(
            question=scoring_input.question,
            description=scoring_input.description,
        )

        # 计算客观性评分
        objectivity_score, objectivity_details = self._calculate_objectivity_score(
            question=scoring_input.question,
            resolution_criteria=scoring_input.resolution_criteria,
            primary_category=scoring_input.primary_category_code,
        )

        # 计算综合评分（加权平均）
        overall_score = (clarity_score * 0.5) + (objectivity_score * 0.5)

        # 确定准入建议
        admission_recommendation, rejection_reason = self._determine_admission(
            clarity_score=clarity_score,
            objectivity_score=objectivity_score,
            overall_score=overall_score,
            classification_confidence=scoring_input.classification_confidence,
        )

        # 组装评分详情
        scoring_details = {
            "clarity": clarity_details,
            "objectivity": objectivity_details,
            "weights": {"clarity": 0.5, "objectivity": 0.5},
            "thresholds": {
                "clarity_min_approved": self.thresholds.clarity_min_approved,
                "objectivity_min_approved": self.thresholds.objectivity_min_approved,
                "overall_min_approved": self.thresholds.overall_min_approved,
            },
        }

        # 写入审计日志
        self._write_audit_log(
            market_ref_id=scoring_input.market_ref_id,
            action="score_market",
            result=admission_recommendation,
            payload={
                "clarity_score": clarity_score,
                "objectivity_score": objectivity_score,
                "overall_score": overall_score,
                "admission_recommendation": admission_recommendation,
                "rejection_reason_code": rejection_reason,
            },
        )

        return ScoringResult(
            market_ref_id=scoring_input.market_ref_id,
            clarity_score=clarity_score,
            resolution_objectivity_score=objectivity_score,
            overall_score=overall_score,
            admission_recommendation=admission_recommendation,
            rejection_reason_code=rejection_reason,
            scoring_details=scoring_details,
            scored_at=datetime.now(timezone.utc),
        )

    def _calculate_clarity_score(
        self,
        question: str,
        description: str | None,
    ) -> tuple[float, dict]:
        """
        计算问题清晰度评分

        评分维度：
        1. 问题长度适中（不过短也不过长）
        2. 包含明确的时间范围或截止日期
        3. 包含可量化的指标或明确的事件
        4. 避免模糊词汇（"可能"、"大约"、"左右"等）
        5. 描述文本的完整性

        Returns:
            (score, details): 评分和详细信息
        """
        details = {}
        score_components = []

        # 1. 问题长度检查（10-200 字符为佳）
        question_len = len(question)
        if 10 <= question_len <= 200:
            length_score = 1.0
        elif question_len < 10:
            length_score = max(0.0, question_len / 10.0)
        else:
            length_score = max(0.3, 1.0 - (question_len - 200) / 300.0)

        details["question_length"] = question_len
        details["length_score"] = length_score
        score_components.append(("length", length_score, 0.2))

        # 2. 时间范围明确性（包含日期、年份、时间词）
        time_patterns = [
            r"\d{4}",  # 年份
            r"\d{1,2}/\d{1,2}",  # 日期
            r"(January|February|March|April|May|June|July|August|September|October|November|December)",
            r"(before|after|by|until|during|in)\s+\d{4}",
            r"(Q[1-4]|H[12])\s+\d{4}",  # 季度/半年
        ]
        time_mentions = sum(1 for pattern in time_patterns if re.search(pattern, question, re.IGNORECASE))
        time_score = min(1.0, time_mentions / 2.0)

        details["time_mentions"] = time_mentions
        details["time_score"] = time_score
        score_components.append(("time_clarity", time_score, 0.25))

        # 3. 可量化指标（数字、百分比、排名等）
        quantifiable_patterns = [
            r"\d+%",  # 百分比
            r"\$\d+",  # 金额
            r"\d+\s*(million|billion|thousand)",
            r"(more than|less than|at least|exceed)\s+\d+",
            r"(top|rank|#)\s*\d+",
        ]
        quantifiable_mentions = sum(
            1 for pattern in quantifiable_patterns if re.search(pattern, question, re.IGNORECASE)
        )
        quantifiable_score = min(1.0, quantifiable_mentions / 2.0)

        details["quantifiable_mentions"] = quantifiable_mentions
        details["quantifiable_score"] = quantifiable_score
        score_components.append(("quantifiable", quantifiable_score, 0.2))

        # 4. 模糊词汇惩罚
        vague_words = [
            "maybe",
            "possibly",
            "probably",
            "might",
            "could",
            "approximately",
            "around",
            "about",
            "roughly",
        ]
        vague_count = sum(1 for word in vague_words if word in question.lower())
        vague_penalty = min(0.5, vague_count * 0.15)
        vague_score = max(0.0, 1.0 - vague_penalty)

        details["vague_word_count"] = vague_count
        details["vague_score"] = vague_score
        score_components.append(("vague_penalty", vague_score, 0.15))

        # 5. 描述完整性
        if description and len(description) > 20:
            description_score = 1.0
        elif description:
            description_score = 0.5
        else:
            description_score = 0.3

        details["has_description"] = description is not None
        details["description_length"] = len(description) if description else 0
        details["description_score"] = description_score
        score_components.append(("description", description_score, 0.2))

        # 计算加权总分
        total_score = sum(score * weight for _, score, weight in score_components)
        details["components"] = [{"name": name, "score": score, "weight": weight} for name, score, weight in score_components]
        details["total_score"] = total_score

        return round(total_score, 4), details

    def _calculate_objectivity_score(
        self,
        question: str,
        resolution_criteria: str | None,
        primary_category: str | None,
    ) -> tuple[float, dict]:
        """
        计算结算客观性评分

        评分维度：
        1. 是否有明确的结算标准
        2. 结算标准是否引用权威数据源
        3. 避免主观判断词汇
        4. 类别本身的客观性（Numeric > Time > Statistical > Person/Macro）
        5. 是否包含可验证的条件

        Returns:
            (score, details): 评分和详细信息
        """
        details = {}
        score_components = []

        # 1. 结算标准存在性
        if resolution_criteria and len(resolution_criteria) > 20:
            criteria_score = 1.0
        elif resolution_criteria:
            criteria_score = 0.5
        else:
            criteria_score = 0.2

        details["has_resolution_criteria"] = resolution_criteria is not None
        details["criteria_length"] = len(resolution_criteria) if resolution_criteria else 0
        details["criteria_score"] = criteria_score
        score_components.append(("criteria_existence", criteria_score, 0.3))

        # 2. 权威数据源引用
        authoritative_sources = [
            "official",
            "government",
            "bureau",
            "agency",
            "commission",
            "reuters",
            "bloomberg",
            "associated press",
            "census",
            "federal",
            "ministry",
            "department of",
        ]
        combined_text = f"{question} {resolution_criteria or ''}".lower()
        source_mentions = sum(1 for source in authoritative_sources if source in combined_text)
        source_score = min(1.0, source_mentions / 2.0)

        details["authoritative_source_mentions"] = source_mentions
        details["source_score"] = source_score
        score_components.append(("authoritative_sources", source_score, 0.25))

        # 3. 主观词汇惩罚
        subjective_words = [
            "believe",
            "think",
            "feel",
            "opinion",
            "seems",
            "appears",
            "likely",
            "unlikely",
            "expected",
            "predicted",
        ]
        subjective_count = sum(1 for word in subjective_words if word in combined_text)
        subjective_penalty = min(0.6, subjective_count * 0.2)
        subjective_score = max(0.0, 1.0 - subjective_penalty)

        details["subjective_word_count"] = subjective_count
        details["subjective_score"] = subjective_score
        score_components.append(("subjective_penalty", subjective_score, 0.2))

        # 4. 类别客观性
        category_objectivity_map = {
            "Numeric": 1.0,
            "Time": 0.95,
            "Statistical": 0.9,
            "Person": 0.7,
            "Macro": 0.7,
            "GeoPolitical": 0.6,
            "Crypto": 0.75,
            "Sports": 0.85,
        }
        category_score = category_objectivity_map.get(primary_category or "", 0.5)

        details["primary_category"] = primary_category
        details["category_score"] = category_score
        score_components.append(("category_objectivity", category_score, 0.15))

        # 5. 可验证条件（数字、日期、事实性陈述）
        verifiable_patterns = [
            r"(will|did|has)\s+(reach|exceed|achieve|announce|release)",
            r"(according to|as reported by|based on)",
            r"(yes|no)\s+(if|when)",
            r"\d+\s*(or more|or less|exactly)",
        ]
        verifiable_count = sum(1 for pattern in verifiable_patterns if re.search(pattern, combined_text, re.IGNORECASE))
        verifiable_score = min(1.0, verifiable_count / 2.0)

        details["verifiable_condition_count"] = verifiable_count
        details["verifiable_score"] = verifiable_score
        score_components.append(("verifiable_conditions", verifiable_score, 0.1))

        # 计算加权总分
        total_score = sum(score * weight for _, score, weight in score_components)
        details["components"] = [{"name": name, "score": score, "weight": weight} for name, score, weight in score_components]
        details["total_score"] = total_score

        return round(total_score, 4), details

    def _determine_admission(
        self,
        clarity_score: float,
        objectivity_score: float,
        overall_score: float,
        classification_confidence: float | None,
    ) -> tuple[str, str | None]:
        """
        根据评分确定准入建议

        Returns:
            (admission_recommendation, rejection_reason_code)
        """
        # 检查是否有任何评分低于最低阈值（直接拒绝）
        if clarity_score < self.thresholds.clarity_min_review:
            return "Rejected", "SCORE_CLARITY_TOO_LOW"

        if objectivity_score < self.thresholds.objectivity_min_review:
            return "Rejected", "SCORE_OBJECTIVITY_TOO_LOW"

        if overall_score < self.thresholds.overall_min_review:
            return "Rejected", "SCORE_OVERALL_TOO_LOW"

        # 检查分类置信度（如果提供）
        if classification_confidence is not None and classification_confidence < 0.5:
            return "ReviewRequired", "CLASSIFICATION_LOW_CONFIDENCE"

        # 检查是否需要人工审核
        needs_review = False
        review_reasons = []

        if clarity_score < self.thresholds.clarity_min_approved:
            needs_review = True
            review_reasons.append("clarity_below_threshold")

        if objectivity_score < self.thresholds.objectivity_min_approved:
            needs_review = True
            review_reasons.append("objectivity_below_threshold")

        if overall_score < self.thresholds.overall_min_approved:
            needs_review = True
            review_reasons.append("overall_below_threshold")

        if needs_review:
            return "ReviewRequired", "SCORE_REQUIRES_REVIEW"

        # 通过所有检查
        return "Approved", None

    def score_and_persist_classification_results(
        self,
        classification_results: list,
        classified_at: datetime,
    ) -> dict:
        """
        对分类结果进行评分并持久化

        Args:
            classification_results: MarketClassificationResult 对象列表
            classified_at: 分类时间

        Returns:
            统计信息字典
        """
        from db.models import Market, MarketScoringResult

        stats = {
            "total": 0,
            "scored": 0,
            "approved": 0,
            "review_required": 0,
            "rejected": 0,
            "errors": 0,
        }

        for result in classification_results:
            stats["total"] += 1

            try:
                # 获取市场信息
                market = self.db.query(Market).filter(Market.id == result.market_ref_id).first()
                if not market:
                    stats["errors"] += 1
                    continue

                # 构建评分输入
                scoring_input = ScoringInput(
                    market_ref_id=market.id,
                    question=market.question,
                    description=market.description,
                    resolution_criteria=market.resolution_criteria,
                    primary_category_code=result.primary_category_code,
                    admission_bucket_code=result.admission_bucket_code,
                    classification_confidence=float(result.confidence) if result.confidence else None,
                )

                # 执行评分
                scoring_result = self.score_market(scoring_input)

                # 检查是否已存在评分结果
                existing = (
                    self.db.query(MarketScoringResult)
                    .filter(
                        MarketScoringResult.market_ref_id == market.id,
                        MarketScoringResult.classification_result_id == result.id,
                    )
                    .first()
                )

                if existing:
                    # 更新现有记录
                    existing.clarity_score = scoring_result.clarity_score
                    existing.resolution_objectivity_score = scoring_result.resolution_objectivity_score
                    existing.overall_score = scoring_result.overall_score
                    existing.admission_recommendation = scoring_result.admission_recommendation
                    existing.rejection_reason_code = scoring_result.rejection_reason_code
                    existing.scoring_details = scoring_result.scoring_details
                    existing.scored_at = scoring_result.scored_at
                else:
                    # 创建新记录
                    scoring_record = MarketScoringResult(
                        market_ref_id=market.id,
                        classification_result_id=result.id,
                        clarity_score=scoring_result.clarity_score,
                        resolution_objectivity_score=scoring_result.resolution_objectivity_score,
                        overall_score=scoring_result.overall_score,
                        admission_recommendation=scoring_result.admission_recommendation,
                        rejection_reason_code=scoring_result.rejection_reason_code,
                        scoring_details=scoring_result.scoring_details,
                        scored_at=scoring_result.scored_at,
                    )
                    self.db.add(scoring_record)

                self.db.flush()

                stats["scored"] += 1
                if scoring_result.admission_recommendation == "Approved":
                    stats["approved"] += 1
                elif scoring_result.admission_recommendation == "ReviewRequired":
                    stats["review_required"] += 1
                elif scoring_result.admission_recommendation == "Rejected":
                    stats["rejected"] += 1

            except Exception as e:
                stats["errors"] += 1
                self.db.rollback()
                print(f"Error scoring market: {e}")

        return stats

    def _write_audit_log(self, market_ref_id: UUID, action: str, result: str, payload: dict):
        """写入审计日志"""
        if not self.audit_service:
            return

        from services.audit.contracts import AuditEvent

        event = AuditEvent(
            actor_id="system",
            actor_type="service",
            object_type="market_scoring",
            object_id=str(market_ref_id),
            action=action,
            result=result,
            task_id=self.task_id,
            event_payload=payload,
        )
        self.audit_service.safe_write_event(event, session=self.db)
