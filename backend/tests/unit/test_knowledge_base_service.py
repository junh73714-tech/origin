"""
知识库服务单元测试

测试 KnowledgeBaseService 的业务逻辑。
使用 mock 隔离数据库依赖。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.document import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBasePermissionCreate,
)
from app.schemas.common import PaginationParams
from app.core.exceptions import (
    BusinessStateError,
    DuplicateResourceError,
    ResourceNotFoundError,
)


def _make_mock_result(value):
    """创建模拟的 SQLAlchemy Result，scalar_one_or_none 返回指定值"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_kb(**kwargs):
    """创建测试用 KnowledgeBase 实例"""
    from app.models.document import KnowledgeBase
    defaults = {
        "id": "kb-001", "tenant_id": "t1", "name": "测试知识库",
        "status": "active", "created_by": "u1",
    }
    defaults.update(kwargs)
    return KnowledgeBase(**defaults)


# =============================================================================
# 创建知识库
# =============================================================================

class TestCreateKnowledgeBase:

    @pytest.mark.asyncio
    async def test_create_kb_success(self):
        """测试成功创建知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        # 同名检查返回空
        mock_db.execute.return_value = _make_mock_result(None)

        service = KnowledgeBaseService(mock_db)
        data = KnowledgeBaseCreate(name="测试知识库", description="测试描述")
        kb = await service.create_knowledge_base("tenant-001", "user-001", data)

        assert kb.name == "测试知识库"
        assert kb.status == "active"
        assert kb.tenant_id == "tenant-001"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_create_kb_duplicate_name(self):
        """测试创建重复名称的知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(_make_kb())

        service = KnowledgeBaseService(mock_db)
        data = KnowledgeBaseCreate(name="测试知识库")
        with pytest.raises(DuplicateResourceError):
            await service.create_knowledge_base("t1", "u1", data)

    @pytest.mark.asyncio
    async def test_create_kb_with_full_data(self):
        """测试使用完整数据创建知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        service = KnowledgeBaseService(mock_db)
        data = KnowledgeBaseCreate(
            name="HR知识库", description="人力资源", is_public=False,
            business_domain="人力资源", settings={"lang": "zh"},
        )
        kb = await service.create_knowledge_base("t1", "u1", data)

        assert kb.business_domain == "人力资源"
        assert kb.settings == {"lang": "zh"}


# =============================================================================
# 查询知识库
# =============================================================================

class TestGetKnowledgeBase:

    @pytest.mark.asyncio
    async def test_get_kb_success(self):
        """测试成功获取知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(id="kb-001", name="测试知识库")
        )

        service = KnowledgeBaseService(mock_db)
        kb = await service.get_knowledge_base("kb-001", tenant_id="t1")
        assert kb.name == "测试知识库"

    @pytest.mark.asyncio
    async def test_get_kb_not_found(self):
        """测试获取不存在的知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        service = KnowledgeBaseService(mock_db)
        with pytest.raises(ResourceNotFoundError):
            await service.get_knowledge_base("non-existent", tenant_id="t1")


# =============================================================================
# 更新知识库
# =============================================================================

class TestUpdateKnowledgeBase:

    @pytest.mark.asyncio
    async def test_update_kb_name(self):
        """测试更新知识库名称"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(name="旧名称")
        )

        service = KnowledgeBaseService(mock_db)
        data = KnowledgeBaseUpdate(name="新名称")
        kb = await service.update_knowledge_base("kb-001", tenant_id="t1", data=data)
        assert kb.name == "新名称"

    @pytest.mark.asyncio
    async def test_update_kb_partial(self):
        """测试部分更新"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(name="原名称", description="原描述")
        )

        service = KnowledgeBaseService(mock_db)
        data = KnowledgeBaseUpdate(description="新描述")
        kb = await service.update_knowledge_base("kb-001", tenant_id="t1", data=data)
        assert kb.name == "原名称"
        assert kb.description == "新描述"

    @pytest.mark.asyncio
    async def test_update_kb_not_found(self):
        """测试更新不存在的知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        service = KnowledgeBaseService(mock_db)
        with pytest.raises(ResourceNotFoundError):
            await service.update_knowledge_base("x", tenant_id="t1", data=KnowledgeBaseUpdate(name="x"))


# =============================================================================
# 启用/停用
# =============================================================================

class TestEnableDisableKnowledgeBase:

    @pytest.mark.asyncio
    async def test_enable_disabled_kb(self):
        """测试启用已停用的知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(status="disabled")
        )

        service = KnowledgeBaseService(mock_db)
        kb = await service.enable_knowledge_base("kb-001", tenant_id="t1")
        assert kb.status == "active"

    @pytest.mark.asyncio
    async def test_enable_already_active(self):
        """测试启用已启用的知识库应失败"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(status="active")
        )

        service = KnowledgeBaseService(mock_db)
        with pytest.raises(BusinessStateError):
            await service.enable_knowledge_base("kb-001", tenant_id="t1")

    @pytest.mark.asyncio
    async def test_disable_active_kb(self):
        """测试停用已启用的知识库"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(status="active")
        )

        service = KnowledgeBaseService(mock_db)
        kb = await service.disable_knowledge_base("kb-001", tenant_id="t1")
        assert kb.status == "disabled"

    @pytest.mark.asyncio
    async def test_disable_already_disabled(self):
        """测试停用已停用的知识库应失败"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(status="disabled")
        )

        service = KnowledgeBaseService(mock_db)
        with pytest.raises(BusinessStateError):
            await service.disable_knowledge_base("kb-001", tenant_id="t1")


# =============================================================================
# 权限管理
# =============================================================================

class TestKnowledgeBasePermissions:

    @pytest.mark.asyncio
    async def test_create_permission_success(self):
        """测试创建知识库权限"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(_make_kb())

        service = KnowledgeBaseService(mock_db)
        data = KnowledgeBasePermissionCreate(
            principal_type="user", principal_id="user-001", permission_type="read",
        )
        perm = await service.create_permission("kb-001", "t1", "admin", data)

        assert perm.knowledge_base_id == "kb-001"
        assert perm.principal_type == "user"
        assert perm.permission_type == "read"

    @pytest.mark.asyncio
    async def test_create_permission_kb_not_found(self):
        """测试为不存在的知识库创建权限"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        service = KnowledgeBaseService(mock_db)
        data = KnowledgeBasePermissionCreate(
            principal_type="user", principal_id="u1", permission_type="read",
        )
        with pytest.raises(ResourceNotFoundError):
            await service.create_permission("non-existent", "t1", "admin", data)


# =============================================================================
# 统计
# =============================================================================

class TestKnowledgeBaseStats:

    @pytest.mark.asyncio
    async def test_get_stats_empty_kb(self):
        """测试空知识库统计"""
        from app.services.knowledge_base import KnowledgeBaseService

        mock_db = AsyncMock()

        # 知识库查询结果
        kb_result = _make_mock_result(_make_kb(status="active"))

        # 使用 SimpleNamespace 构造统计查询结果
        # 注意：execute 返回的 Result 调用 .one() 得到行对象
        def _make_stats_row(**fields):
            row = MagicMock()
            for k, v in fields.items():
                setattr(row, k, v)
            # .one() 调用返回这个行对象
            result = MagicMock()
            result.one.return_value = row
            return result

        doc_result = _make_stats_row(total=0, published=0, processing=0, failed=0)
        chunk_result = _make_stats_row(total=0, total_tokens=0, indexed=0)
        task_result = _make_stats_row(pending=0, failed=0)

        mock_db.execute.side_effect = [kb_result, doc_result, chunk_result, task_result]

        service = KnowledgeBaseService(mock_db)
        stats = await service.get_knowledge_base_stats("kb-001", tenant_id="t1")

        assert stats.knowledge_base_id == "kb-001"
        assert stats.document_count == 0
        assert stats.chunk_count == 0
        assert stats.index_task_pending == 0
