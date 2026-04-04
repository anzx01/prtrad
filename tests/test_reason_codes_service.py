"""
单元测试：拒绝原因码服务
"""
import pytest

from services.reason_codes import ReasonCodeService, ReasonCodeInput, ReasonCodeUpdate


class TestReasonCodeService:
    """测试拒绝原因码服务"""

    def test_create_reason_code(self, test_db):
        """测试创建原因码"""
        session = test_db()
        service = ReasonCodeService(db=session)

        input_data = ReasonCodeInput(
            reason_code="TEST_001",
            reason_name="Test Reason",
            reason_category="classification",
            description="Test description",
            severity="high",
            sort_order=10
        )

        result = service.create_reason_code(input_data)
        session.commit()

        assert result.reason_code == "TEST_001"
        assert result.reason_name == "Test Reason"
        assert result.reason_category == "classification"
        assert result.severity == "high"
        assert result.is_active is True

        session.close()

    def test_list_reason_codes_empty(self, test_db):
        """测试空列表"""
        session = test_db()
        service = ReasonCodeService(db=session)

        codes = service.list_reason_codes()
        assert codes == []

        session.close()
