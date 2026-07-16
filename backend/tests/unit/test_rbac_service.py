"""
成员4：RBAC服务单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.rbac_service import (
    create_permission,
    create_role,
    get_permission_by_code,
    get_role_by_code,
    assign_role_to_user,
    can_execute_action,
)


class TestRBACService:
    """RBAC服务测试"""

    @pytest.mark.asyncio
    async def test_create_permission(self):
        """测试创建权限"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await create_permission(
            mock_db,
            name="测试权限",
            code="test.permission",
            resource_type="test",
            action="read",
            description="测试描述",
            created_by="system",
        )
        assert result is not None
        assert result.code == "test.permission"
        assert result.name == "测试权限"

    @pytest.mark.asyncio
    async def test_create_role(self):
        """测试创建角色"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await create_role(
            mock_db,
            name="测试角色",
            code="test_role",
            description="测试角色描述",
            is_system=False,
            created_by="system",
        )
        assert result is not None
        assert result.code == "test_role"
        assert result.name == "测试角色"

    @pytest.mark.asyncio
    async def test_get_permission_by_code(self):
        """测试根据编码获取权限"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        perm = await get_permission_by_code(mock_db, "query.test.permission")
        assert perm is None

    @pytest.mark.asyncio
    async def test_can_execute_action_no_permission(self):
        """测试无权限用户执行操作"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        result = await can_execute_action(mock_db, "non_existent_user", "any.action")
        assert result is False
