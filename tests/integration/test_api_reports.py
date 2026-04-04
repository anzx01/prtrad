"""
集成测试：报告 API
"""
import pytest
from fastapi.testclient import TestClient


class TestReportsAPI:
    """测试报告 API"""

    def test_list_reports(self, client: TestClient):
        """测试获取报告列表"""
        response = client.get("/reports")
        assert response.status_code == 200

        data = response.json()
        assert "reports" in data
        assert isinstance(data["reports"], list)
