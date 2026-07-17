"""
知识库 API 端点测试

使用 FastAPI TestClient + dependency_overrides 测试全部10个端点。
Mock Service 层，测试 API 的路由和响应格式。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.document import KnowledgeBase


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def client(mock_db):
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_kb_resp(**kwargs):
    """创建完整的 KnowledgeBase 实例（模拟 DB 返回的已持久化对象）"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    kb = KnowledgeBase(
        id=kwargs.get("id", "kb-001"),
        tenant_id=kwargs.get("tenant_id", "default"),
        name=kwargs.get("name", "测试知识库"),
        description=kwargs.get("description", None),
        icon=kwargs.get("icon", None),
        is_public=kwargs.get("is_public", False),
        status=kwargs.get("status", "active"),
        business_domain=kwargs.get("business_domain", None),
        settings=kwargs.get("settings", None),
        document_count=kwargs.get("document_count", 0),
        chunk_count=kwargs.get("chunk_count", 0),
        created_by=kwargs.get("created_by", "system"),
    )
    # 手动设置 server_default 字段（模拟 flush 后的状态）
    kb.created_at = kwargs.get("created_at", now)
    kb.updated_at = kwargs.get("updated_at", now)
    kb.updated_by = kwargs.get("updated_by", None)
    return kb


# =============================================================================
# 创建知识库
# =============================================================================

class TestCreateKnowledgeBase:

    def test_create_success(self, client, mock_db):
        """测试创建知识库成功"""
        kb = _make_kb_resp(name="新知识库", description="测试用")

        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.create_knowledge_base = AsyncMock(return_value=kb)

            response = client.post("/api/v1/knowledge-bases", json={
                "name": "新知识库",
                "description": "测试用",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "新知识库"

    def test_create_empty_name(self, client, mock_db):
        """测试名称为空"""
        response = client.post("/api/v1/knowledge-bases", json={"name": ""})
        assert response.status_code == 422


# =============================================================================
# 查询知识库列表
# =============================================================================

class TestListKnowledgeBases:

    def test_list_empty(self, client, mock_db):
        """测试空列表"""
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_knowledge_bases = AsyncMock(return_value=([], 0))

            response = client.get("/api/v1/knowledge-bases")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []

    def test_list_with_data(self, client, mock_db):
        """测试有数据的列表"""
        kb = _make_kb_resp(name="HR知识库")
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_knowledge_bases = AsyncMock(return_value=([kb], 1))

            response = client.get("/api/v1/knowledge-bases?keyword=HR")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
        assert len(data["data"]["items"]) == 1


# =============================================================================
# 获取知识库详情
# =============================================================================

class TestGetKnowledgeBase:

    def test_get_success(self, client, mock_db):
        """测试获取详情"""
        kb = _make_kb_resp(name="详情测试")
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_knowledge_base = AsyncMock(return_value=kb)

            response = client.get("/api/v1/knowledge-bases/kb-001")

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "详情测试"

    def test_get_not_found(self, client, mock_db):
        """测试404"""
        from app.core.exceptions import ResourceNotFoundError
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_knowledge_base = AsyncMock(
                side_effect=ResourceNotFoundError("知识库", "x")
            )
            response = client.get("/api/v1/knowledge-bases/non-existent")

        assert response.status_code == 404


# =============================================================================
# 编辑
# =============================================================================

class TestUpdateKnowledgeBase:

    def test_update_success(self, client, mock_db):
        """测试编辑"""
        kb = _make_kb_resp(name="新名称", description="新描述")
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.update_knowledge_base = AsyncMock(return_value=kb)

            response = client.put("/api/v1/knowledge-bases/kb-001", json={
                "name": "新名称",
                "description": "新描述",
            })

        assert response.status_code == 200


# =============================================================================
# 启用/停用
# =============================================================================

class TestEnableDisableKnowledgeBase:

    def test_enable(self, client, mock_db):
        kb = _make_kb_resp(status="active")
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.enable_knowledge_base = AsyncMock(return_value=kb)

            response = client.patch("/api/v1/knowledge-bases/kb-001/enable")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"

    def test_disable(self, client, mock_db):
        kb = _make_kb_resp(status="disabled")
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.disable_knowledge_base = AsyncMock(return_value=kb)

            response = client.patch("/api/v1/knowledge-bases/kb-001/disable")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "disabled"


# =============================================================================
# 统计
# =============================================================================

class TestKnowledgeBaseStats:

    def test_stats(self, client, mock_db):
        from app.schemas.document import KnowledgeBaseStatsResponse
        stats = KnowledgeBaseStatsResponse(
            knowledge_base_id="kb-001",
            document_count=5, published_count=3,
            processing_count=1, failed_count=1,
            chunk_count=50, indexed_chunk_count=45,
            total_tokens=5000, index_task_pending=2, index_task_failed=1,
        )
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_knowledge_base_stats = AsyncMock(return_value=stats)

            response = client.get("/api/v1/knowledge-bases/kb-001/stats")

        assert response.status_code == 200
        assert response.json()["data"]["document_count"] == 5


# =============================================================================
# 权限管理
# =============================================================================

class TestKnowledgeBasePermissions:

    def test_create_permission(self, client, mock_db):
        from app.models.document import KnowledgeBasePermission
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        perm = KnowledgeBasePermission(
            id="kp-001", tenant_id="default", knowledge_base_id="kb-001",
            principal_type="user", principal_id="u1",
            permission_type="read", is_deny=False,
            created_by="admin",
        )
        perm.created_at = now
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.create_permission = AsyncMock(return_value=perm)

            response = client.post("/api/v1/knowledge-bases/kb-001/permissions", json={
                "principal_type": "user",
                "principal_id": "user-001",
                "permission_type": "read",
            })

        assert response.status_code == 200
        assert response.json()["data"]["principal_type"] == "user"

    def test_create_permission_kb_not_found(self, client, mock_db):
        from app.core.exceptions import ResourceNotFoundError
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.create_permission = AsyncMock(
                side_effect=ResourceNotFoundError("知识库", "x")
            )
            response = client.post("/api/v1/knowledge-bases/x/permissions", json={
                "principal_type": "user", "principal_id": "u1", "permission_type": "read",
            })

        assert response.status_code == 404

    def test_list_permissions(self, client, mock_db):
        from app.models.document import KnowledgeBasePermission
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        perm = KnowledgeBasePermission(
            id="kp-001", tenant_id="default", knowledge_base_id="kb-001",
            principal_type="user", principal_id="u1",
            permission_type="read", is_deny=False,
            created_by="admin",
        )
        perm.created_at = now
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_permissions = AsyncMock(return_value=[perm])

            response = client.get("/api/v1/knowledge-bases/kb-001/permissions")

        assert response.status_code == 200
        assert len(response.json()["data"]) == 1

    def test_delete_permission(self, client, mock_db):
        with patch("app.api.knowledge_bases.KnowledgeBaseService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.delete_permission = AsyncMock(return_value=None)

            response = client.delete("/api/v1/knowledge-bases/kb-001/permissions/kp-001")

        assert response.status_code == 204
