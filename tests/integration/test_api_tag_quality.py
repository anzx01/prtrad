"""
集成测试：标签质量 API
"""
import pytest
from fastapi.testclient import TestClient


class TestTagQualityAPI:
    """测试标签质量 API"""

    def test_get_metrics(self, client: TestClient):
        """测试获取质量指标"""
        response = client.get("/tag-quality/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "metrics" in data
        assert isinstance(data["metrics"], list)
