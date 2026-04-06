"""
种子数据脚本：为 Tag Quality 和 List Management 填充测试数据
"""
import sys
import uuid
from datetime import datetime, timedelta, UTC
from decimal import Decimal

sys.path.insert(0, ".")

from sqlalchemy import text
from db.session import SessionLocal
from db.models import (
    TagQualityMetric, TagQualityAnomaly,
    ListEntry,
)


def seed_tag_quality(db):
    """生成最近 7 天的标签质量数据"""
    db.execute(text("DELETE FROM tag_quality_metrics"))
    db.execute(text("DELETE FROM tag_quality_anomalies"))
    db.commit()

    now = datetime.now(UTC)
    for i in range(7):
        day = now - timedelta(days=i)
        metric = TagQualityMetric(
            id=uuid.uuid4(),
            metric_date=day.replace(hour=0, minute=0, second=0, microsecond=0),
            rule_version="dq_v1",
            total_classifications=120 - i * 3,
            success_count=110 - i * 2,
            failure_count=5,
            conflict_count=i,
            avg_confidence=Decimal("0.85") - Decimal(str(i * 0.02)),
            category_distribution={},
            bucket_distribution={},
        )
        db.add(metric)

    # 一条未解决异常
    anomaly = TagQualityAnomaly(
        id=uuid.uuid4(),
        anomaly_type="success_rate_drop",
        severity="warning",
        detected_at=now - timedelta(hours=3),
        rule_version="dq_v1",
        anomaly_details={"success_rate": 0.72, "threshold": 0.80},
        is_resolved=False,
        created_at=now,
    )
    db.add(anomaly)
    db.commit()
    print("[OK] Created 7 TagQualityMetric + 1 TagQualityAnomaly")


def seed_list_management(db):
    """创建名单条目"""
    db.execute(text("DELETE FROM list_entries WHERE added_by='seed_script'"))
    db.commit()

    now = datetime.now(UTC)

    samples = [
        ("blacklist", "keyword", "pump_and_dump"),
        ("blacklist", "keyword", "rug_pull"),
        ("whitelist", "market_id", "market_123456"),
        ("whitelist", "market_id", "market_789012"),
        ("greylist", "keyword", "uncertain_outcome"),
        ("greylist", "keyword", "low_liquidity"),
    ]

    for list_type, entry_type, value in samples:
        entry = ListEntry(
            id=uuid.uuid4(),
            list_type=list_type,
            entry_type=entry_type,
            entry_value=value,
            match_mode="exact",
            reason="Seed data for development",
            added_by="seed_script",
            is_active=True,
        )
        db.add(entry)

    db.commit()
    print(f"[OK] Created {len(samples)} ListEntry (blacklist/whitelist/greylist)")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_tag_quality(db)
        seed_list_management(db)
        print("\n[DONE] Seed data complete!")
    finally:
        db.close()
