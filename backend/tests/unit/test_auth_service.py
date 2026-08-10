"""
成员4：认证服务单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.security import get_password_hash, verify_password
from app.services.auth_service import check_login_lockout


class TestPasswordSecurity:
    """密码安全测试"""

    def test_password_hash_verify(self):
        """测试密码哈希与校验"""
        password = "Test@123456"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

    def test_password_hash_different(self):
        """测试相同密码生成不同哈希"""
        password = "Test@123456"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2


class TestLoginLockout:
    """登录锁定测试"""

    @pytest.mark.asyncio
    async def test_no_lockout_initially(self):
        """初始状态不应锁定"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        locked = await check_login_lockout(mock_db, "test_user")
        assert locked is False
