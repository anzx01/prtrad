"""
集成测试：拒绝原因码 API
"""
import pytest
from fastapi.testclient import TestClient


class TestReasonCodesAPI:
    """测试拒绝原因码 API"""

    def test_list_reason_codes_empty(self, client: TestClient):
        """测试获取空原因码列表"""
        response = client.get("/reason-codes")
        assert response.status_code == 200

        data = response.json()
        assert "codes" in data
        assert "total" in data
        assert data["total"] == 0
        assert data["codes"] == []

    def test_list_reason_codes_with_filter(self, client: TestClient):
        """测试带过滤的原因码列表"""
        # 测试按类别过滤
        response = client.get("/reason-codes?category=classification")
        assert response.status_code == 200

        # 测试包含非活跃
        response = client.get("/reason-codes?include_inactive=true")
        assert response.status_code == 200

    def test_get_reason_code_not_found(self, client: TestClient):
        """测试获取不存在的原因码"""
        response = client.get("/reason-codes/NOT_EXIST")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
