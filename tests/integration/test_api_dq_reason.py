from datetime import UTC, datetime
from decimal import Decimal
import uuid

from db.models import DataQualityResult, Market


def test_get_dq_reason_samples_empty(client):
    response = client.get("/dq/reasons/REJ_DATA_LEAK_RISK")
    assert response.status_code == 200

    data = response.json()
    assert data["reason_code"] == "REJ_DATA_LEAK_RISK"
    assert data["latest_checked_at"] is None
    assert data["total_matches"] == 0
    assert data["check_counts"] == []
    assert data["missing_field_counts"] == []
    assert data["samples"] == []


def test_get_dq_reason_samples_focuses_latest_batch_and_matching_checks(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    latest_checked_at = datetime(2026, 4, 18, 2, 0, tzinfo=UTC)
    previous_checked_at = datetime(2026, 4, 17, 2, 0, tzinfo=UTC)
    creation_time = datetime(2026, 4, 10, 0, 0, tzinfo=UTC)
    open_time = datetime(2026, 4, 11, 0, 0, tzinfo=UTC)
    close_time = datetime(2026, 4, 17, 12, 0, tzinfo=UTC)
    latest_snapshot_time = datetime(2026, 4, 18, 3, 0, tzinfo=UTC)
    previous_snapshot_time = datetime(2026, 4, 18, 2, 30, tzinfo=UTC)

    try:
        matched_market = Market(
            id=uuid.uuid4(),
            market_id="leak-risk-market",
            question="Leak risk market?",
            market_status="active_accepting_orders",
            creation_time=creation_time,
            open_time=open_time,
            close_time=close_time,
            source_updated_at=datetime(2026, 4, 18, 1, 55, tzinfo=UTC),
        )
        other_market = Market(
            id=uuid.uuid4(),
            market_id="stale-market",
            question="Stale market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime(2026, 4, 18, 1, 50, tzinfo=UTC),
        )
        session.add_all([matched_market, other_market])
        session.commit()

        session.add_all(
            [
                DataQualityResult(
                    id=uuid.uuid4(),
                    market_ref_id=matched_market.id,
                    checked_at=previous_checked_at,
                    status="fail",
                    score=Decimal("0.40"),
                    failure_count=1,
                    result_details={
                        "blocking_reason_codes": ["REJ_DATA_STALE"],
                        "warning_reason_codes": [],
                        "checks": [
                            {
                                "code": "DQ_SNAPSHOT_STALE",
                                "status": "fail",
                                "severity": "error",
                                "message": "旧批次样本",
                                "blocking": True,
                                "reason_code": "REJ_DATA_STALE",
                                "details": {"age_seconds": 600},
                            }
                        ],
                    },
                    rule_version="dq_v1",
                ),
                DataQualityResult(
                    id=uuid.uuid4(),
                    market_ref_id=matched_market.id,
                    checked_at=latest_checked_at,
                    status="fail",
                    score=Decimal("0.60"),
                    failure_count=2,
                    result_details={
                        "blocking_reason_codes": ["REJ_DATA_LEAK_RISK"],
                        "warning_reason_codes": ["REJ_DATA_STALE"],
                        "checks": [
                            {
                                "code": "DQ_ACTIVE_MARKET_SNAPSHOT_AFTER_CLOSE",
                                "status": "fail",
                                "severity": "error",
                                "message": "活跃市场的最新快照时间晚于 close_time。",
                                "blocking": True,
                                "reason_code": "REJ_DATA_LEAK_RISK",
                                "details": None,
                            },
                            {
                                "code": "DQ_SNAPSHOT_AFTER_CHECKED_AT",
                                "status": "fail",
                                "severity": "error",
                                "message": "快照时间晚于 DQ 检查时间，存在未来数据泄漏风险。",
                                "blocking": True,
                                "reason_code": "REJ_DATA_LEAK_RISK",
                                "details": {"delta_seconds": 3600},
                            },
                        ],
                        "latest_snapshot": {"snapshot_time": latest_snapshot_time.isoformat()},
                        "previous_snapshot": {"snapshot_time": previous_snapshot_time.isoformat()},
                    },
                    rule_version="dq_v1",
                ),
                DataQualityResult(
                    id=uuid.uuid4(),
                    market_ref_id=other_market.id,
                    checked_at=latest_checked_at,
                    status="fail",
                    score=Decimal("0.50"),
                    failure_count=1,
                    result_details={
                        "blocking_reason_codes": ["REJ_DATA_STALE"],
                        "warning_reason_codes": [],
                        "checks": [
                            {
                                "code": "DQ_SNAPSHOT_STALE",
                                "status": "fail",
                                "severity": "error",
                                "message": "最新快照已超过允许新鲜度阈值。",
                                "blocking": True,
                                "reason_code": "REJ_DATA_STALE",
                                "details": {"age_seconds": 601},
                            }
                        ],
                    },
                    rule_version="dq_v1",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/reasons/REJ_DATA_LEAK_RISK?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert data["reason_code"] == "REJ_DATA_LEAK_RISK"
    assert data["latest_checked_at"] == latest_checked_at.replace(tzinfo=None).isoformat()
    assert data["total_matches"] == 1
    assert data["check_counts"] == [
        {"code": "DQ_ACTIVE_MARKET_SNAPSHOT_AFTER_CLOSE", "count": 1},
        {"code": "DQ_SNAPSHOT_AFTER_CHECKED_AT", "count": 1},
    ]
    assert data["missing_field_counts"] == []

    sample = data["samples"][0]
    assert sample["market_id"] == "leak-risk-market"
    assert sample["status"] == "fail"
    assert sample["blocking_reason_codes"] == ["REJ_DATA_LEAK_RISK"]
    assert sample["warning_reason_codes"] == ["REJ_DATA_STALE"]
    assert len(sample["matching_checks"]) == 2
    assert sample["matching_checks"][0]["code"] == "DQ_ACTIVE_MARKET_SNAPSHOT_AFTER_CLOSE"
    assert sample["matching_checks"][1]["details"] == {"delta_seconds": 3600}
    assert sample["timestamps"]["creation_time"] == creation_time.isoformat()
    assert sample["timestamps"]["open_time"] == open_time.isoformat()
    assert sample["timestamps"]["close_time"] == close_time.isoformat()
    assert sample["timestamps"]["latest_snapshot_time"] == latest_snapshot_time.isoformat()
    assert sample["timestamps"]["previous_snapshot_time"] == previous_snapshot_time.isoformat()


def test_get_dq_reason_samples_aggregates_missing_fields_for_incomplete_reason(client):
    from tests.integration.conftest import TestSessionLocal

    session = TestSessionLocal()
    latest_checked_at = datetime(2026, 4, 18, 6, 0, tzinfo=UTC)

    try:
        market_a = Market(
            id=uuid.uuid4(),
            market_id="incomplete-market-a",
            question="Incomplete market A?",
            market_status="active_accepting_orders",
            source_updated_at=datetime(2026, 4, 18, 5, 55, tzinfo=UTC),
        )
        market_b = Market(
            id=uuid.uuid4(),
            market_id="incomplete-market-b",
            question="Incomplete market B?",
            market_status="active_accepting_orders",
            source_updated_at=datetime(2026, 4, 18, 5, 56, tzinfo=UTC),
        )
        market_other = Market(
            id=uuid.uuid4(),
            market_id="non-incomplete-market",
            question="Non incomplete market?",
            market_status="active_accepting_orders",
            source_updated_at=datetime(2026, 4, 18, 5, 57, tzinfo=UTC),
        )
        session.add_all([market_a, market_b, market_other])
        session.commit()

        session.add_all(
            [
                DataQualityResult(
                    id=uuid.uuid4(),
                    market_ref_id=market_a.id,
                    checked_at=latest_checked_at,
                    status="fail",
                    score=Decimal("0.60"),
                    failure_count=2,
                    result_details={
                        "blocking_reason_codes": ["REJ_DATA_INCOMPLETE"],
                        "warning_reason_codes": [],
                        "checks": [
                            {
                                "code": "DQ_MARKET_REQUIRED_FIELDS_MISSING",
                                "status": "fail",
                                "severity": "error",
                                "message": "市场关键字段缺失。",
                                "blocking": True,
                                "reason_code": "REJ_DATA_INCOMPLETE",
                                "details": {"missing_fields": ["description", "close_time"]},
                            },
                            {
                                "code": "DQ_SNAPSHOT_REQUIRED_FIELDS_MISSING",
                                "status": "fail",
                                "severity": "error",
                                "message": "最新快照缺少关键字段。",
                                "blocking": True,
                                "reason_code": "REJ_DATA_INCOMPLETE",
                                "details": {"missing_fields": ["best_bid_no", "best_ask_no"]},
                            },
                        ],
                    },
                    rule_version="dq_v1",
                ),
                DataQualityResult(
                    id=uuid.uuid4(),
                    market_ref_id=market_b.id,
                    checked_at=latest_checked_at,
                    status="fail",
                    score=Decimal("0.55"),
                    failure_count=1,
                    result_details={
                        "blocking_reason_codes": ["REJ_DATA_INCOMPLETE"],
                        "warning_reason_codes": [],
                        "checks": [
                            {
                                "code": "DQ_SNAPSHOT_REQUIRED_FIELDS_MISSING",
                                "status": "fail",
                                "severity": "error",
                                "message": "最新快照缺少关键字段。",
                                "blocking": True,
                                "reason_code": "REJ_DATA_INCOMPLETE",
                                "details": {"missing_fields": ["best_ask_no", "spread"]},
                            }
                        ],
                    },
                    rule_version="dq_v1",
                ),
                DataQualityResult(
                    id=uuid.uuid4(),
                    market_ref_id=market_other.id,
                    checked_at=latest_checked_at,
                    status="fail",
                    score=Decimal("0.40"),
                    failure_count=1,
                    result_details={
                        "blocking_reason_codes": ["REJ_DATA_STALE"],
                        "warning_reason_codes": [],
                        "checks": [
                            {
                                "code": "DQ_SNAPSHOT_STALE",
                                "status": "fail",
                                "severity": "error",
                                "message": "最新快照已超过允许新鲜度阈值。",
                                "blocking": True,
                                "reason_code": "REJ_DATA_STALE",
                                "details": {"age_seconds": 900},
                            }
                        ],
                    },
                    rule_version="dq_v1",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/dq/reasons/REJ_DATA_INCOMPLETE?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert data["reason_code"] == "REJ_DATA_INCOMPLETE"
    assert data["total_matches"] == 2
    assert data["check_counts"] == [
        {"code": "DQ_SNAPSHOT_REQUIRED_FIELDS_MISSING", "count": 2},
        {"code": "DQ_MARKET_REQUIRED_FIELDS_MISSING", "count": 1},
    ]

    missing_field_counts = {item["field_name"]: item for item in data["missing_field_counts"]}
    assert missing_field_counts["best_ask_no"]["count"] == 2
    assert missing_field_counts["best_ask_no"]["check_codes"] == ["DQ_SNAPSHOT_REQUIRED_FIELDS_MISSING"]
    assert missing_field_counts["description"]["count"] == 1
    assert missing_field_counts["description"]["check_codes"] == ["DQ_MARKET_REQUIRED_FIELDS_MISSING"]
    assert missing_field_counts["close_time"]["count"] == 1
    assert missing_field_counts["best_bid_no"]["count"] == 1
    assert missing_field_counts["spread"]["count"] == 1
