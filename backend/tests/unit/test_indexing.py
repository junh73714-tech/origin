"""
索引服务单元测试

测试 IndexingService 的任务管理和索引写入功能。
使用 mock 隔离 OpenSearch、pgvector 和 Embedding API。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.indexing import build_idempotent_key


# =============================================================================
# 幂等键测试
# =============================================================================

class TestIdempotentKey:

    def test_build_key(self):
        """测试构建幂等键"""
        key = build_idempotent_key("ver-001", "chunk-001", "opensearch")
        assert len(key) == 32
        assert isinstance(key, str)

    def test_same_input_same_key(self):
        """测试相同输入产生相同幂等键"""
        k1 = build_idempotent_key("v1", "c1", "os")
        k2 = build_idempotent_key("v1", "c1", "os")
        assert k1 == k2

    def test_different_input_different_key(self):
        """测试不同输入产生不同幂等键"""
        k1 = build_idempotent_key("v1", "c1", "opensearch")
        k2 = build_idempotent_key("v1", "c1", "pgvector")
        assert k1 != k2

    def test_different_chunk_different_key(self):
        """测试不同Chunk产生不同幂等键"""
        k1 = build_idempotent_key("v1", "chunk-a", "opensearch")
        k2 = build_idempotent_key("v1", "chunk-b", "opensearch")
        assert k1 != k2


# =============================================================================
# IndexTask 管理测试
# =============================================================================

class TestIndexTaskManagement:

    @pytest.mark.asyncio
    async def test_create_index_task(self):
        """测试创建索引任务"""
        from app.services.indexing import IndexingService

        mock_db = AsyncMock()

        with patch("app.services.indexing.EmbeddingProvider"), \
             patch("app.services.indexing.OpenSearch"):
            service = IndexingService(mock_db)
            task = await service.create_index_task(
                tenant_id="t1",
                document_id="doc-001",
                document_version_id="ver-001",
                task_type="create",
                target="both",
            )

            assert task.task_type == "create"
            assert task.target == "both"
            assert task.status == "pending"
            assert task.retry_count == 0
            assert len(task.idempotent_key) > 0

    @pytest.mark.asyncio
    async def test_create_index_task_with_chunk(self):
        """测试创建单Chunk索引任务"""
        from app.services.indexing import IndexingService

        mock_db = AsyncMock()

        with patch("app.services.indexing.EmbeddingProvider"), \
             patch("app.services.indexing.OpenSearch"):
            service = IndexingService(mock_db)
            task = await service.create_index_task(
                tenant_id="t1",
                document_id="doc-001",
                document_version_id="ver-001",
                task_type="update",
                target="pgvector",
                chunk_id="chunk-001",
            )

            assert task.chunk_id == "chunk-001"
            assert task.target == "pgvector"

    @pytest.mark.asyncio
    async def test_create_task_task_types(self):
        """测试所有任务类型"""
        from app.services.indexing import IndexingService

        mock_db = AsyncMock()

        with patch("app.services.indexing.EmbeddingProvider"), \
             patch("app.services.indexing.OpenSearch"):
            service = IndexingService(mock_db)
            for ttype in ["create", "update", "delete", "rebuild", "consistency_check"]:
                task = await service.create_index_task(
                    tenant_id="t1", document_id="d1",
                    document_version_id="v1", task_type=ttype,
                )
                assert task.task_type == ttype


# =============================================================================
# 索引一致性测试
# =============================================================================

class TestConsistency:

    @pytest.mark.asyncio
    async def test_consistency_check_empty(self):
        """测试一致性检查（无Chunk）"""
        from app.services.indexing import IndexingService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch("app.services.indexing.EmbeddingProvider"), \
             patch("app.services.indexing.OpenSearch"):
            service = IndexingService(mock_db)
            result = await service.consistency_check()

            assert result["total_chunks"] == 0
            assert result["missing_opensearch"] == 0
            assert result["missing_pgvector"] == 0
