"""
单元测试：名单管理服务
"""
import pytest

from services.lists import ListService
from db.models import ListEntry


class TestListService:
    """测试名单管理服务"""

    def test_list_entries_empty(self, test_db):
        """测试空名单"""
        session = test_db()
        service = ListService(db=session)
        entries = service.list_entries()
        assert entries == []
        session.close()
