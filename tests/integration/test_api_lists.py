"""
集成测试：名单管理 API
"""
import pytest
from fastapi.testclient import TestClient


class TestListsAPI:
    """测试名单管理 API"""

    def test_list_entries_empty(self, client: TestClient):
        """测试获取空名单"""
        response = client.get("/lists/entries")
        assert response.status_code == 200

        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] == 0
        assert data["entries"] == []

    def test_list_entries_with_filter(self, client: TestClient):
        """测试带过滤的名单查询"""
        # 测试按类型过滤
        response = client.get("/lists/entries?list_type=whitelist")
        assert response.status_code == 200

        data = response.json()
        assert "entries" in data
        assert "total" in data
