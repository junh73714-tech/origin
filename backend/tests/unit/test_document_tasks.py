"""
Celery 文档处理任务测试

绕过消息队列，直接 await 异步任务函数进行测试。
不依赖 Redis/Celery Worker。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# process_document_task 测试
# =============================================================================

class TestProcessDocumentTask:

    @pytest.mark.asyncio
    async def test_process_document_success(self):
        """测试文档处理任务成功执行"""
        # Mock 返回结果
        expected_result = {
            "document_id": "doc-001",
            "status": "pending_review",
            "chunk_count": 3,
            "indexed_count": 3,
            "parse_quality": "good",
        }

        mock_orchestrator = MagicMock()
        mock_orchestrator.process_document = AsyncMock(return_value=expected_result)

        # Mock 数据库上下文
        mock_db = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.tasks.document.get_db_context", return_value=mock_ctx), \
             patch("app.services.orchestrator.DocumentOrchestrator", return_value=mock_orchestrator):

            from app.tasks.document import process_document_task

            result = await process_document_task(document_id="doc-001", tenant_id="default")

            assert result["document_id"] == "doc-001"
            assert result["status"] == "pending_review"
            assert result["chunk_count"] == 3

    @pytest.mark.asyncio
    async def test_process_document_retry_on_failure(self):
        """测试处理失败时触发重试"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.process_document = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        mock_db = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.tasks.document.get_db_context", return_value=mock_ctx), \
             patch("app.services.orchestrator.DocumentOrchestrator", return_value=mock_orchestrator):

            from app.tasks.document import process_document_task

            # 任务应触发 retry
            with pytest.raises(Exception):
                await process_document_task(document_id="doc-001")


# =============================================================================
# process_version_update_task 测试
# =============================================================================

class TestVersionUpdateTask:

    @pytest.mark.asyncio
    async def test_version_update_success(self):
        """测试版本更新任务成功"""
        from app.models.document import DocumentVersion

        mock_version = DocumentVersion(
            id="ver-002", tenant_id="t1", document_id="doc-001",
            knowledge_base_id="kb-001", version=2, file_path="path/v2.pdf",
            file_size=2048, file_hash="hash2", created_by="u1",
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.update_document_version = AsyncMock(return_value={
            "document_id": "doc-001",
            "old_version": 1,
            "new_version": 2,
            "diff": {"added": 1, "deleted": 0, "unchanged": 2, "modified": 0},
            "new_chunks": 3,
            "status": "pending_review",
        })

        mock_db = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = mock_version
        mock_db.execute.return_value = version_result

        with patch("app.tasks.document.get_db_context", return_value=mock_ctx), \
             patch("app.services.orchestrator.DocumentOrchestrator", return_value=mock_orchestrator):

            from app.tasks.document import process_version_update_task

            result = await process_version_update_task(
                document_id="doc-001", version_id="ver-002"
            )

            assert result["old_version"] == 1
            assert result["new_version"] == 2
            assert result["diff"]["added"] == 1

    @pytest.mark.asyncio
    async def test_version_update_version_not_found(self):
        """测试版本不存在时任务失败"""
        mock_db = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = version_result

        with patch("app.tasks.document.get_db_context", return_value=mock_ctx):

            from app.tasks.document import process_version_update_task

            with pytest.raises(Exception):
                await process_version_update_task(
                    document_id="doc-001", version_id="non-existent"
                )


# =============================================================================
# index_batch_task 测试
# =============================================================================

class TestIndexBatchTask:

    @pytest.mark.asyncio
    async def test_index_batch_success(self):
        """测试批量索引任务"""
        from app.models.document import DocumentChunk, DocumentVersion

        mock_chunks = [
            DocumentChunk(
                id="c1", tenant_id="t1", knowledge_base_id="kb1",
                document_id="d1", document_version_id="v1",
                chunk_no=1, raw_text="t1", clean_text="t1",
                content_hash="h1", created_by="u1",
            )
        ]
        mock_version = DocumentVersion(
            id="v1", tenant_id="t1", document_id="d1",
            knowledge_base_id="kb1", version=1, file_path="p",
            file_size=100, file_hash="h", created_by="u1",
        )

        mock_db = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        # 第一次 execute: 获取 IndexTask
        task_mock = MagicMock()
        task_mock.status = "pending"
        task_mock.document_version_id = "v1"
        task_mock.retry_count = 0
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = task_mock

        # 第二次 execute: 获取 chunks
        chunk_result = MagicMock()
        chunk_result.scalars.return_value.all.return_value = mock_chunks

        # 第三次 execute: 获取 version
        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = mock_version

        mock_db.execute.side_effect = [task_result, chunk_result, version_result]

        with patch("app.tasks.document.get_db_context", return_value=mock_ctx), \
             patch("app.services.indexing.IndexingService") as mock_idx_cls:

            mock_indexing = MagicMock()
            mock_indexing.index_chunks_batch = AsyncMock(return_value={
                "total": 1, "opensearch_success": 1, "pgvector_success": 1
            })
            mock_idx_cls.return_value = mock_indexing

            from app.tasks.document import index_batch_task

            result = await index_batch_task(task_ids=["task-001"])

            assert result["total_tasks"] == 1
            assert result["success"] == 1


# =============================================================================
# consistency_check_task 测试
# =============================================================================

class TestConsistencyCheckTask:

    @pytest.mark.asyncio
    async def test_consistency_check_success(self):
        """测试一致性检查任务"""
        mock_db = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.tasks.document.get_db_context", return_value=mock_ctx), \
             patch("app.services.indexing.IndexingService") as mock_idx_cls:

            mock_indexing = MagicMock()
            mock_indexing.consistency_check = AsyncMock(return_value={
                "total_chunks": 50,
                "missing_opensearch": 0,
                "missing_pgvector": 2,
                "model_mismatch": 0,
                "fixed": 0,
            })
            mock_idx_cls.return_value = mock_indexing

            from app.tasks.document import consistency_check_task

            result = await consistency_check_task(
                knowledge_base_id="kb-001", auto_fix=False
            )

            assert result["total_chunks"] == 50
            assert result["missing_opensearch"] == 0
            assert result["missing_pgvector"] == 2
