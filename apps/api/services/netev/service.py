"""M3 NetEV 准入评估服务"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from db.models import (
    CalibrationUnit,
    DataQualityResult,
    DecisionLog,
    Market,
    MarketScoringResult,
    MarketSnapshot,
    NetEVCandidate,
    RejectionReasonCode,
    RejectionReasonStats,
)
from services.calibration.service import MIN_ACTIVE_SAMPLE_COUNT
from services.m3_helpers import (
    decimal_or_none,
    liquidity_tier_from_snapshot,
    midpoint_from_snapshot,
    normalize_category,
    price_bucket_from_probability,
    quantize_6,
    time_bucket_from_market,
    utc_now,
)


NETEV_MIN_THRESHOLD = Decimal("0.005")


@dataclass(frozen=True)
class ReasonCatalogEntry:
    reason_name: str
    reason_category: str
    description: str
    severity: str
    sort_order: int


def _coerce_reason_codes(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


REASON_CATALOG: dict[str, ReasonCatalogEntry] = {
    "SCORING_RESULT_MISSING": ReasonCatalogEntry(
        reason_name="缺少评分结果",
        reason_category="netev",
        description="市场尚未完成 M2 评分，无法进入 NetEV 评估。",
        severity="high",
        sort_order=300,
    ),
    "SCORE_NOT_APPROVED": ReasonCatalogEntry(
        reason_name="评分未通过准入",
        reason_category="netev",
        description="市场评分未达到可进入 NetEV 评估的基线。",
        severity="high",
        sort_order=305,
    ),
    "DQ_RESULT_MISSING": ReasonCatalogEntry(
        reason_name="缺少 DQ 结果",
        reason_category="netev",
        description="市场缺少最新数据质量结果，无法继续。",
        severity="high",
        sort_order=310,
    ),
    "DQ_NOT_PASS": ReasonCatalogEntry(
        reason_name="数据质量未通过",
        reason_category="netev",
        description="最新数据质量结果不是 pass，市场被下游屏蔽。",
        severity="high",
        sort_order=315,
    ),
    "SNAPSHOT_MISSING": ReasonCatalogEntry(
        reason_name="缺少可用快照",
        reason_category="netev",
        description="无法提取最新价格或流动性快照。",
        severity="high",
        sort_order=320,
    ),
    "CALIBRATION_UNIT_MISSING": ReasonCatalogEntry(
        reason_name="缺少校准单元",
        reason_category="netev",
        description="当前候选找不到匹配的历史校准单元。",
        severity="high",
        sort_order=325,
    ),
    "CALIBRATION_SAMPLE_TOO_LOW": ReasonCatalogEntry(
        reason_name="校准样本不足",
        reason_category="netev",
        description="历史样本不足，校准单元不能作为稳定的交易输入。",
        severity="high",
        sort_order=330,
    ),
    "NETEV_BELOW_THRESHOLD": ReasonCatalogEntry(
        reason_name="成本后边际不足",
        reason_category="netev",
        description="扣除费用、滑点和争议折扣后，NetEV 未达到最低阈值。",
        severity="medium",
        sort_order=335,
    ),
    "SCORE_CLARITY_TOO_LOW": ReasonCatalogEntry(
        reason_name="清晰度评分过低",
        reason_category="scoring",
        description="市场问题表述不够清晰。",
        severity="high",
        sort_order=200,
    ),
    "SCORE_OBJECTIVITY_TOO_LOW": ReasonCatalogEntry(
        reason_name="客观性评分过低",
        reason_category="scoring",
        description="结算标准不够客观。",
        severity="high",
        sort_order=205,
    ),
    "SCORE_OVERALL_TOO_LOW": ReasonCatalogEntry(
        reason_name="综合评分过低",
        reason_category="scoring",
        description="综合评分未达到最低阈值。",
        severity="high",
        sort_order=210,
    ),
    "CLASSIFICATION_LOW_CONFIDENCE": ReasonCatalogEntry(
        reason_name="分类置信度不足",
        reason_category="scoring",
        description="分类结果置信度偏低，需要人工确认。",
        severity="medium",
        sort_order=215,
    ),
    "SCORE_REQUIRES_REVIEW": ReasonCatalogEntry(
        reason_name="评分需人工审核",
        reason_category="scoring",
        description="评分处于人工审核区间，暂不进入自动准入。",
        severity="medium",
        sort_order=220,
    ),
    "REJ_DATA_STALE": ReasonCatalogEntry(
        reason_name="数据过期",
        reason_category="data",
        description="快照或源数据已经过期。",
        severity="high",
        sort_order=100,
    ),
    "REJ_DATA_INCOMPLETE": ReasonCatalogEntry(
        reason_name="数据不完整",
        reason_category="data",
        description="关键价格或流动性字段缺失。",
        severity="high",
        sort_order=105,
    ),
    "REJ_DATA_LEAK_RISK": ReasonCatalogEntry(
        reason_name="存在信息泄漏风险",
        reason_category="data",
        description="时间或结算字段存在泄漏风险。",
        severity="critical",
        sort_order=110,
    ),
    "REJ_DATA_ANOMALY": ReasonCatalogEntry(
        reason_name="发现数据异常",
        reason_category="data",
        description="价格或流动性出现异常跳变。",
        severity="high",
        sort_order=115,
    ),
}


class NetEVService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def evaluate(self, market_id: uuid.UUID, *, window_type: str = "long") -> NetEVCandidate | None:
        market = self.db.get(Market, market_id)
        if not market:
            return None

        latest_scoring = self._latest_scoring_result(market_id)
        latest_dq = self._latest_dq_result(market_id)
        latest_snapshot = self._latest_snapshot(market_id)

        category_code = normalize_category(market.category_raw)
        price_bucket: str | None = None
        time_bucket: str | None = None
        liquidity_tier: str | None = None

        gross_edge = Decimal("0")
        fee_cost = Decimal("0")
        slippage_cost = Decimal("0")
        dispute_discount = Decimal("0")
        net_ev = Decimal("0")
        admission_decision = "reject"
        rejection_reason_code: str | None = None
        calibration_unit: CalibrationUnit | None = None

        snapshot_midpoint = midpoint_from_snapshot(latest_snapshot) if latest_snapshot else None
        if snapshot_midpoint is not None and latest_snapshot is not None:
            price_bucket = price_bucket_from_probability(snapshot_midpoint)
            time_bucket = time_bucket_from_market(market, reference_time=latest_snapshot.snapshot_time)
            liquidity_tier = liquidity_tier_from_snapshot(latest_snapshot)

        if latest_scoring is None:
            rejection_reason_code = "SCORING_RESULT_MISSING"
        elif latest_snapshot is None or snapshot_midpoint is None:
            rejection_reason_code = "SNAPSHOT_MISSING"
        elif latest_dq is None:
            rejection_reason_code = "DQ_RESULT_MISSING"
        elif (latest_dq.status or "").lower() != "pass":
            rejection_reason_code = self._dq_reason_code(latest_dq)
        elif latest_scoring.admission_recommendation != "Approved":
            rejection_reason_code = latest_scoring.rejection_reason_code or "SCORE_NOT_APPROVED"
        else:
            calibration_unit = self._select_best_unit(
                category_code=category_code,
                price_bucket=price_bucket or "p50_70",
                time_bucket=time_bucket or "unknown",
                liquidity_tier=liquidity_tier or "standard",
                window_type=window_type,
            )
            if calibration_unit is None:
                rejection_reason_code = "CALIBRATION_UNIT_MISSING"
            elif not calibration_unit.is_active or calibration_unit.sample_count < MIN_ACTIVE_SAMPLE_COUNT:
                rejection_reason_code = "CALIBRATION_SAMPLE_TOO_LOW"
            else:
                gross_edge = self._estimate_gross_edge(calibration_unit, latest_scoring)
                fee_cost = self._estimate_fee(snapshot_midpoint)
                slippage_cost = self._estimate_slippage(latest_snapshot)
                dispute_discount = self._estimate_dispute_discount(latest_scoring, category_code)
                net_ev = quantize_6(gross_edge - fee_cost - slippage_cost - dispute_discount)

                if net_ev >= NETEV_MIN_THRESHOLD:
                    admission_decision = "admit"
                    rejection_reason_code = None
                else:
                    admission_decision = "reject"
                    rejection_reason_code = "NETEV_BELOW_THRESHOLD"

        input_timestamps = [
            latest_snapshot.snapshot_time if latest_snapshot else None,
            latest_dq.checked_at if latest_dq else None,
            latest_scoring.scored_at if latest_scoring else None,
            calibration_unit.computed_at if calibration_unit else None,
        ]
        latest_input_at = max((ts for ts in input_timestamps if ts is not None), default=None)
        latest_candidate = self._latest_candidate(market_id)
        if latest_candidate and latest_input_at and latest_candidate.evaluated_at >= latest_input_at:
            return latest_candidate

        evaluated_at = utc_now()
        self._ensure_reason_codes()

        candidate = NetEVCandidate(
            id=uuid.uuid4(),
            market_ref_id=market_id,
            calibration_unit_id=calibration_unit.id if calibration_unit else None,
            gross_edge=gross_edge,
            fee_cost=fee_cost,
            slippage_cost=slippage_cost,
            dispute_discount=dispute_discount,
            net_ev=net_ev,
            admission_decision=admission_decision,
            rejection_reason_code=rejection_reason_code,
            evaluated_at=evaluated_at,
        )
        self.db.add(candidate)
        self.db.flush()

        self._write_decision_log(
            market=market,
            candidate=candidate,
            category_code=category_code,
            price_bucket=price_bucket,
            time_bucket=time_bucket,
            liquidity_tier=liquidity_tier,
            scoring_result=latest_scoring,
            dq_result=latest_dq,
            calibration_unit=calibration_unit,
            window_type=window_type,
        )

        if rejection_reason_code:
            self._increment_reason_stat(rejection_reason_code, evaluated_at)

        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def evaluate_batch(self, *, limit: int = 20, window_type: str = "long") -> list[NetEVCandidate]:
        recent_scoring_results = list(
            self.db.scalars(
                select(MarketScoringResult).order_by(MarketScoringResult.scored_at.desc())
            ).all()
        )

        market_ids: list[uuid.UUID] = []
        seen_market_ids: set[uuid.UUID] = set()
        for scoring_result in recent_scoring_results:
            if scoring_result.market_ref_id in seen_market_ids:
                continue
            seen_market_ids.add(scoring_result.market_ref_id)
            market_ids.append(scoring_result.market_ref_id)
            if len(market_ids) >= limit:
                break

        candidates: list[NetEVCandidate] = []
        for market_id in market_ids:
            candidate = self.evaluate(market_id, window_type=window_type)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def list_candidates(self, decision: str | None = None) -> list[NetEVCandidate]:
        stmt = select(NetEVCandidate)
        if decision:
            stmt = stmt.where(NetEVCandidate.admission_decision == decision)
        stmt = stmt.order_by(NetEVCandidate.evaluated_at.desc())
        return list(self.db.scalars(stmt).all())

    def list_candidate_views(self, decision: str | None = None) -> list[dict]:
        return [self.get_candidate_view(candidate) for candidate in self.list_candidates(decision=decision)]

    def get_candidate_view(self, candidate: NetEVCandidate) -> dict:
        market = self.db.get(Market, candidate.market_ref_id)
        calibration_unit = None
        if candidate.calibration_unit_id:
            calibration_unit = self.db.get(CalibrationUnit, candidate.calibration_unit_id)

        latest_scoring = self._latest_scoring_result(candidate.market_ref_id)
        latest_dq = self._latest_dq_result(candidate.market_ref_id)
        reason_details = self._resolve_reason_details(candidate.rejection_reason_code)
        dq_blocking_reason_codes: list[str] = []
        dq_warning_reason_codes: list[str] = []
        dq_primary_reason_code: str | None = None
        dq_primary_reason_details: ReasonCatalogEntry | None = None

        if latest_dq is not None:
            dq_details = latest_dq.result_details if isinstance(latest_dq.result_details, dict) else {}
            dq_blocking_reason_codes = _coerce_reason_codes(dq_details.get("blocking_reason_codes"))
            dq_warning_reason_codes = _coerce_reason_codes(dq_details.get("warning_reason_codes"))
            dq_primary_reason_code = (
                dq_blocking_reason_codes[0]
                if dq_blocking_reason_codes
                else dq_warning_reason_codes[0]
                if dq_warning_reason_codes
                else None
            )
            dq_primary_reason_details = self._resolve_reason_details(dq_primary_reason_code)

        return {
            "id": candidate.id,
            "market_ref_id": candidate.market_ref_id,
            "market_id": market.market_id if market else None,
            "question": market.question if market else None,
            "category_code": normalize_category(market.category_raw if market else None),
            "calibration_unit_id": candidate.calibration_unit_id,
            "calibration_sample_count": calibration_unit.sample_count if calibration_unit else None,
            "price_bucket": calibration_unit.price_bucket if calibration_unit else None,
            "time_bucket": calibration_unit.time_bucket if calibration_unit else None,
            "liquidity_tier": calibration_unit.liquidity_tier if calibration_unit else None,
            "window_type": calibration_unit.window_type if calibration_unit else None,
            "gross_edge": float(candidate.gross_edge),
            "fee_cost": float(candidate.fee_cost),
            "slippage_cost": float(candidate.slippage_cost),
            "dispute_discount": float(candidate.dispute_discount),
            "net_ev": float(candidate.net_ev),
            "admission_decision": candidate.admission_decision,
            "rejection_reason_code": candidate.rejection_reason_code,
            "rejection_reason_name": reason_details.reason_name if reason_details else None,
            "rejection_reason_description": reason_details.description if reason_details else None,
            "scoring_recommendation": latest_scoring.admission_recommendation if latest_scoring else None,
            "dq_status": latest_dq.status if latest_dq else None,
            "dq_checked_at": latest_dq.checked_at if latest_dq else None,
            "dq_blocking_reason_codes": dq_blocking_reason_codes,
            "dq_warning_reason_codes": dq_warning_reason_codes,
            "dq_primary_reason_code": dq_primary_reason_code,
            "dq_primary_reason_name": dq_primary_reason_details.reason_name if dq_primary_reason_details else None,
            "dq_primary_reason_description": dq_primary_reason_details.description if dq_primary_reason_details else None,
            "rule_version": self.settings.rule_version,
            "evaluated_at": candidate.evaluated_at,
        }

    def _latest_snapshot(self, market_id: uuid.UUID):
        return self.db.scalar(
            select(MarketSnapshot)
            .where(MarketSnapshot.market_ref_id == market_id)
            .order_by(MarketSnapshot.snapshot_time.desc())
        )

    def _latest_dq_result(self, market_id: uuid.UUID) -> DataQualityResult | None:
        return self.db.scalar(
            select(DataQualityResult)
            .where(DataQualityResult.market_ref_id == market_id)
            .order_by(DataQualityResult.checked_at.desc())
        )

    def _latest_scoring_result(self, market_id: uuid.UUID) -> MarketScoringResult | None:
        return self.db.scalar(
            select(MarketScoringResult)
            .where(MarketScoringResult.market_ref_id == market_id)
            .order_by(MarketScoringResult.scored_at.desc())
        )

    def _latest_candidate(self, market_id: uuid.UUID) -> NetEVCandidate | None:
        return self.db.scalar(
            select(NetEVCandidate)
            .where(NetEVCandidate.market_ref_id == market_id)
            .order_by(NetEVCandidate.evaluated_at.desc())
        )

    def _select_best_unit(
        self,
        *,
        category_code: str,
        price_bucket: str,
        time_bucket: str,
        liquidity_tier: str,
        window_type: str,
    ) -> CalibrationUnit | None:
        candidates = list(
            self.db.scalars(
                select(CalibrationUnit)
                .where(CalibrationUnit.category_code == category_code)
                .where(CalibrationUnit.price_bucket == price_bucket)
                .where(CalibrationUnit.window_type == window_type)
                .where(CalibrationUnit.is_active.is_(True))
            ).all()
        )
        if not candidates:
            candidates = list(
                self.db.scalars(
                    select(CalibrationUnit)
                    .where(CalibrationUnit.category_code == category_code)
                    .where(CalibrationUnit.window_type == window_type)
                    .where(CalibrationUnit.is_active.is_(True))
                ).all()
            )
        if not candidates:
            return None

        def sort_key(unit: CalibrationUnit):
            return (
                0 if unit.time_bucket == time_bucket else 1,
                0 if unit.liquidity_tier == liquidity_tier else 1,
                -unit.sample_count,
                abs(float(unit.edge_estimate)),
            )

        candidates.sort(key=sort_key)
        return candidates[0]

    def _estimate_gross_edge(self, calibration_unit: CalibrationUnit, scoring_result: MarketScoringResult) -> Decimal:
        base_edge = decimal_or_none(calibration_unit.edge_estimate) or Decimal("0")
        score_weight = decimal_or_none(scoring_result.overall_score) or Decimal("0.75")
        return quantize_6(base_edge * max(Decimal("0.75"), score_weight))

    def _estimate_fee(self, midpoint: Decimal) -> Decimal:
        return quantize_6(max(Decimal("0.0015"), midpoint * Decimal("0.006")))

    def _estimate_slippage(self, snapshot) -> Decimal:
        spread = abs(decimal_or_none(snapshot.spread) or Decimal("0"))
        depth = decimal_or_none(snapshot.cumulative_depth_at_target_size)
        if depth is None:
            depth = decimal_or_none(snapshot.top_of_book_depth)
        depth = depth or Decimal("0")

        if depth < Decimal("250"):
            depth_penalty = Decimal("0.020")
        elif depth < Decimal("1000"):
            depth_penalty = Decimal("0.010")
        elif depth < Decimal("5000"):
            depth_penalty = Decimal("0.004")
        else:
            depth_penalty = Decimal("0.002")

        return quantize_6((spread / Decimal("2")) + depth_penalty)

    def _estimate_dispute_discount(self, scoring_result: MarketScoringResult, category_code: str) -> Decimal:
        objectivity = decimal_or_none(scoring_result.resolution_objectivity_score) or Decimal("0.5")
        score_penalty = max(Decimal("0"), Decimal("0.75") - objectivity) * Decimal("0.02")
        category_penalty = Decimal("0.002") if category_code.lower() in {"politics", "macro", "person"} else Decimal("0")
        return quantize_6(Decimal("0.001") + score_penalty + category_penalty)

    def _dq_reason_code(self, dq_result: DataQualityResult) -> str:
        details = dq_result.result_details or {}
        if isinstance(details, dict):
            blocking_reason_codes = details.get("blocking_reason_codes")
            if isinstance(blocking_reason_codes, list) and blocking_reason_codes:
                return str(blocking_reason_codes[0])
        return "DQ_NOT_PASS"

    def _write_decision_log(
        self,
        *,
        market: Market,
        candidate: NetEVCandidate,
        category_code: str,
        price_bucket: str | None,
        time_bucket: str | None,
        liquidity_tier: str | None,
        scoring_result: MarketScoringResult | None,
        dq_result: DataQualityResult | None,
        calibration_unit: CalibrationUnit | None,
        window_type: str,
    ) -> None:
        decision_log = DecisionLog(
            id=uuid.uuid4(),
            market_ref_id=market.id,
            signal_id=str(candidate.id),
            decision_type="netev_admission",
            decision_status=candidate.admission_decision,
            primary_reason_code=candidate.rejection_reason_code,
            secondary_reason_codes=None,
            payload={
                "window_type": window_type,
                "category_code": category_code,
                "price_bucket": price_bucket,
                "time_bucket": time_bucket,
                "liquidity_tier": liquidity_tier,
                "gross_edge": float(candidate.gross_edge),
                "fee_cost": float(candidate.fee_cost),
                "slippage_cost": float(candidate.slippage_cost),
                "dispute_discount": float(candidate.dispute_discount),
                "net_ev": float(candidate.net_ev),
                "scoring_recommendation": scoring_result.admission_recommendation if scoring_result else None,
                "dq_status": dq_result.status if dq_result else None,
                "calibration_sample_count": calibration_unit.sample_count if calibration_unit else None,
            },
            rule_version=self.settings.rule_version,
        )
        self.db.add(decision_log)

    def _increment_reason_stat(self, reason_code: str, evaluated_at: datetime) -> None:
        stat_date = evaluated_at.replace(hour=0, minute=0, second=0, microsecond=0)
        stat = self.db.scalar(
            select(RejectionReasonStats).where(
                RejectionReasonStats.reason_code == reason_code,
                RejectionReasonStats.stat_date == stat_date,
            )
        )
        if stat is None:
            stat = RejectionReasonStats(
                id=uuid.uuid4(),
                reason_code=reason_code,
                stat_date=stat_date,
                occurrence_count=1,
            )
            self.db.add(stat)
        else:
            stat.occurrence_count += 1

    def _ensure_reason_codes(self) -> None:
        existing_codes = {
            code.reason_code
            for code in self.db.scalars(select(RejectionReasonCode)).all()
        }
        for reason_code, catalog_entry in REASON_CATALOG.items():
            if reason_code in existing_codes:
                continue
            self.db.add(
                RejectionReasonCode(
                    id=uuid.uuid4(),
                    reason_code=reason_code,
                    reason_name=catalog_entry.reason_name,
                    reason_category=catalog_entry.reason_category,
                    description=catalog_entry.description,
                    severity=catalog_entry.severity,
                    is_active=True,
                    sort_order=catalog_entry.sort_order,
                )
            )
        self.db.flush()

    def _resolve_reason_details(self, reason_code: str | None) -> ReasonCatalogEntry | None:
        if reason_code is None:
            return None

        persisted = self.db.scalar(
            select(RejectionReasonCode).where(RejectionReasonCode.reason_code == reason_code)
        )
        if persisted is not None:
            return ReasonCatalogEntry(
                reason_name=persisted.reason_name,
                reason_category=persisted.reason_category,
                description=persisted.description or "",
                severity=persisted.severity,
                sort_order=persisted.sort_order,
            )

        return REASON_CATALOG.get(reason_code)


