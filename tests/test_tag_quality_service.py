"""
单元测试：标签质量服务
"""
import pytest

from services.tag_quality import TagQualityService


class TestTagQualityService:
    """测试标签质量服务"""

    def test_get_metrics_empty(self, test_db):
        """测试获取空质量指标"""
        session = test_db()
        service = TagQualityService(db=session)
        metrics = service.get_metrics()

        assert isinstance(metrics, list)
        assert metrics == []

        session.close()
