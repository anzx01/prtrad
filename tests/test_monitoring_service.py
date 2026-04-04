"""
单元测试：监控服务
"""
import pytest

from services.monitoring import MonitoringService


class TestMonitoringService:
    """测试监控服务"""

    def test_get_metrics(self, test_db):
        """测试获取监控指标"""
        session = test_db()
        service = MonitoringService(db=session)
        metrics = service.get_metrics()

        assert isinstance(metrics, dict)
        assert "status" in metrics
        assert metrics["status"] == "ok"

        session.close()
