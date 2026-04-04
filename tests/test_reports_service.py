"""
单元测试：报告服务
"""
import pytest

from services.reports import ReportService


class TestReportService:
    """测试报告服务"""

    def test_list_reports_empty(self, test_db):
        """测试获取空报告列表"""
        session = test_db()
        service = ReportService(db=session)
        reports = service.list_reports()

        assert isinstance(reports, list)
        assert reports == []

        session.close()
