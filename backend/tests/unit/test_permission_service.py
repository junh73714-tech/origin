"""
成员4：PermissionService单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.permission_service import PermissionService


class TestPermissionService:
    """权限服务测试"""

    @pytest.mark.asyncio
    async def test_can_execute_action_default_deny(self):
        """测试默认拒绝规则"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        service = PermissionService(mock_db)
        result = await service.can_execute_action("non_existent_user", "document.read")
        assert result is False

    @pytest.mark.asyncio
    async def test_build_retrieval_filters(self):
        """测试构建检索过滤条件"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.tenant_id = "default"
        mock_user.id = "test_user"
        mock_user.roles = []
        mock_user.departments = []
        mock_user.groups = []
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        service = PermissionService(mock_db)
        filters = await service.build_retrieval_filters("test_user")
        assert filters is not None
        assert filters.user_id == "test_user"
        assert filters.scope_hash is not None

    @pytest.mark.asyncio
    async def test_build_opensearch_filter(self):
        """测试构建OpenSearch过滤条件"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.tenant_id = "default"
        mock_user.id = "test_user"
        mock_user.roles = []
        mock_user.departments = []
        mock_user.groups = []
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        service = PermissionService(mock_db)
        opensearch_filter = await service.build_opensearch_filter("test_user")
        assert opensearch_filter is not None

    @pytest.mark.asyncio
    async def test_build_postgresql_filter(self):
        """测试构建PostgreSQL过滤条件"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.tenant_id = "default"
        mock_user.id = "test_user"
        mock_user.roles = []
        mock_user.departments = []
        mock_user.groups = []
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        service = PermissionService(mock_db)
        pg_filter = await service.build_postgresql_filter("test_user")
        assert pg_filter is not None
