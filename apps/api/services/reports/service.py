"""报告服务"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.models import M2Report


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def list_reports(self):
        """获取所有报告，按生成时间倒序"""
        reports = self.db.scalars(
            select(M2Report).order_by(M2Report.generated_at.desc())
        ).all()

        return [
            {
                "id": str(report.id),
                "report_type": report.report_type,
                "report_period_start": report.report_period_start.isoformat(),
                "report_period_end": report.report_period_end.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "generated_by": report.generated_by,
                "report_data": report.report_data,
            }
            for report in reports
        ]
