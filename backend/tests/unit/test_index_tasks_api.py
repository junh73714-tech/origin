"""
索引任务 API 端点测试

Mock Service 层，测试 API 路由和响应格式。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db


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


def _make_task(**kwargs):
    """创建完整 IndexTask 实例"""
    from app.models.document import IndexTask
    task = IndexTask(
        id=kwargs.get("id", "task-001"),
        tenant_id=kwargs.get("tenant_id", "default"),
        document_id=kwargs.get("document_id", "doc-001"),
        document_version_id=kwargs.get("document_version_id", "ver-001"),
        task_type=kwargs.get("task_type", "create"),
        target=kwargs.get("target", "both"),
        idempotent_key=kwargs.get("idempotent_key", "key123"),
        status=kwargs.get("status", "pending"),
        retry_count=kwargs.get("retry_count", 0),
        max_retries=kwargs.get("max_retries", 3),
        progress=kwargs.get("progress", 0),
        total_chunks=kwargs.get("total_chunks", 10),
        indexed_chunks=kwargs.get("indexed_chunks", 0),
        error_message=kwargs.get("error_message", None),
        created_by=kwargs.get("created_by", "system"),
    )
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    task.created_at = kwargs.get("created_at", now)
    task.started_at = kwargs.get("started_at", None)
    task.completed_at = kwargs.get("completed_at", None)
    task.updated_at = now
    task.updated_by = None
    return task


# =============================================================================
# 列表
# =============================================================================

class TestListIndexTasks:

    def test_empty(self, client, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/index-tasks")
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 0

    def test_with_data(self, client, mock_db):
        task = _make_task()
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [task]
        mock_db.execute.side_effect = [count_result, list_result]

        response = client.get("/api/v1/index-tasks?status=failed")
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 1


# =============================================================================
# 详情
# =============================================================================

class TestGetIndexTask:

    def test_success(self, client, mock_db):
        task = _make_task(task_type="rebuild")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/index-tasks/task-001")
        assert response.status_code == 200
        assert response.json()["data"]["task_type"] == "rebuild"

    def test_not_found(self, client, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/index-tasks/non-existent")
        assert response.status_code == 404


# =============================================================================
# 重试
# =============================================================================

class TestRetryIndexTask:

    def test_success(self, client, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_task(status="failed")
        mock_db.execute.return_value = mock_result

        response = client.post("/api/v1/index-tasks/task-001/retry")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "pending"

    def test_not_failed(self, client, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_task(status="completed")
        mock_db.execute.return_value = mock_result

        response = client.post("/api/v1/index-tasks/task-001/retry")
        assert response.status_code == 400


# =============================================================================
# 重建
# =============================================================================

class TestRebuildIndex:

    def test_success(self, client, mock_db):
        task = _make_task(task_type="rebuild")
        with patch("app.api.index_tasks.IndexingService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.create_index_task = AsyncMock(return_value=task)

            response = client.post("/api/v1/index-tasks/rebuild", json={
                "knowledge_base_id": "kb-001",
            })

        assert response.status_code == 200
        assert response.json()["data"]["task_type"] == "rebuild"


# =============================================================================
# 一致性检查
# =============================================================================

class TestConsistencyCheck:

    def test_success(self, client, mock_db):
        with patch("app.api.index_tasks.IndexingService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.consistency_check = AsyncMock(return_value={
                "total_chunks": 50, "missing_opensearch": 0,
                "missing_pgvector": 2, "model_mismatch": 0, "fixed": 0,
            })

            response = client.post("/api/v1/index-tasks/consistency-check", json={
                "knowledge_base_id": "kb-001", "auto_fix": False,
            })

        assert response.status_code == 200
        assert response.json()["data"]["total_chunks"] == 50

    def test_without_body(self, client, mock_db):
        with patch("app.api.index_tasks.IndexingService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.consistency_check = AsyncMock(return_value={
                "total_chunks": 0, "missing_opensearch": 0,
                "missing_pgvector": 0, "model_mismatch": 0, "fixed": 0,
            })

            response = client.post("/api/v1/index-tasks/consistency-check")

        assert response.status_code == 200
