#!/usr/bin/env python3
"""Initialize sample report data"""
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path
import uuid

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from db.models import M2Report
from db.session import session_scope


def seed_reports():
    """Insert sample report data"""
    with session_scope() as session:
        # Check if reports already exist
        existing = session.query(M2Report).count()
        if existing > 0:
            print(f"Found {existing} existing reports, skipping seed")
            return

        now = datetime.now(UTC)

        # Create 3 sample reports
        reports = [
            M2Report(
                id=uuid.uuid4(),
                report_type="weekly_summary",
                report_period_start=now - timedelta(days=7),
                report_period_end=now,
                generated_at=now,
                generated_by="system",
                created_at=now,
                report_data={
                    "total_markets": 1234,
                    "high_risk_markets": 45,
                    "medium_risk_markets": 120,
                    "low_risk_markets": 1069,
                    "reviewed_count": 30,
                    "approved_count": 22,
                    "rejected_count": 8,
                },
            ),
            M2Report(
                id=uuid.uuid4(),
                report_type="tagging_quality",
                report_period_start=now - timedelta(days=30),
                report_period_end=now,
                generated_at=now - timedelta(days=1),
                generated_by="system",
                created_at=now - timedelta(days=1),
                report_data={
                    "total_tagged": 5000,
                    "accuracy_rate": 0.945,
                    "conflicts_detected": 12,
                    "manual_reviews": 25,
                    "categories": {
                        "politics": {"count": 1200, "accuracy": 0.98},
                        "sports": {"count": 800, "accuracy": 0.92},
                        "crypto": {"count": 1500, "accuracy": 0.94},
                        "other": {"count": 1500, "accuracy": 0.93},
                    },
                },
            ),
            M2Report(
                id=uuid.uuid4(),
                report_type="risk_assessment",
                report_period_start=now - timedelta(days=14),
                report_period_end=now,
                generated_at=now - timedelta(days=2),
                generated_by="system",
                created_at=now - timedelta(days=2),
                report_data={
                    "assessment_date": now.isoformat(),
                    "critical_alerts": 3,
                    "warning_alerts": 28,
                    "info_alerts": 156,
                    "top_risks": [
                        {
                            "market_id": "market_001",
                            "question": "Will Bitcoin reach $100k by EOY 2026?",
                            "risk_score": 8.5,
                            "reason": "High volatility, low liquidity",
                        },
                        {
                            "market_id": "market_002",
                            "question": "Will Trump win 2028 election?",
                            "risk_score": 7.8,
                            "reason": "Political uncertainty, resolution complexity",
                        },
                    ],
                },
            ),
        ]

        for report in reports:
            session.add(report)

        session.commit()
        print(f"Successfully initialized {len(reports)} sample reports")


if __name__ == "__main__":
    seed_reports()
