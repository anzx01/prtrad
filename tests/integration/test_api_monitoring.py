"""
集成测试：监控 API
"""
import pytest
from fastapi.testclient import TestClient


class TestMonitoringAPI:
    """测试监控 API"""

    def test_get_metrics(self, client: TestClient):
        """测试获取监控指标"""
        response = client.get("/monitoring/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "metrics" in data
        assert isinstance(data["metrics"], dict)
