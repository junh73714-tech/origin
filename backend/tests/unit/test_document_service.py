"""
文档服务单元测试

测试 DocumentService 的业务逻辑。
使用 mock 隔离数据库和MinIO依赖。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import (
    BusinessStateError,
    ResourceNotFoundError,
    ValidationError,
    StorageError,
)
from app.schemas.document import DocumentListParams
from app.schemas.common import PaginationParams


def _make_mock_result(value):
    """创建模拟的 SQLAlchemy Result"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_doc(**kwargs):
    """创建测试用 Document 实例"""
    from app.models.document import Document
    defaults = {
        "id": "doc-001", "tenant_id": "t1", "knowledge_base_id": "kb-001",
        "name": "test.pdf", "original_filename": "test.pdf",
        "file_type": "pdf", "mime_type": "application/pdf",
        "file_size": 1024, "file_hash": "hash123", "file_path": "path/key.pdf",
        "status": "draft", "current_version": 1, "created_by": "u1",
    }
    defaults.update(kwargs)
    return Document(**defaults)


def _make_kb(**kwargs):
    """创建测试用 KnowledgeBase 实例"""
    from app.models.document import KnowledgeBase
    defaults = {"id": "kb-001", "tenant_id": "t1", "name": "KB", "status": "active", "created_by": "u1"}
    defaults.update(kwargs)
    return KnowledgeBase(**defaults)


# =============================================================================
# 文档上传测试
# =============================================================================

class TestDocumentUpload:

    @pytest.mark.asyncio
    async def test_upload_success(self):
        """测试成功上传文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()

        # 知识库验证 -> 返回有效KB
        # 重复检查 -> 返回None
        # 文档创建后flush (两次)
        # 知识库计数更新
        kb_result = _make_mock_result(_make_kb())
        dup_result = _make_mock_result(None)
        kb_update_result = _make_mock_result(_make_kb())

        with patch("app.services.document.MinioStorageService") as mock_storage_cls:
            mock_storage = MagicMock()
            mock_storage.upload_file.return_value = {
                "bucket": "docs", "key": "path/key.pdf", "size": 1024, "etag": "abc",
            }
            mock_storage_cls.return_value = mock_storage

            mock_db.execute.side_effect = [
                kb_result,    # _verify_knowledge_base
                dup_result,   # 重复检查
                kb_update_result,  # _increment_kb_document_count
            ]

            service = DocumentService(mock_db)
            doc = await service.upload_document(
                tenant_id="t1", user_id="u1", knowledge_base_id="kb-001",
                filename="test.pdf", file_data=b"test content",
                mime_type="application/pdf",
            )

            assert doc.name == "test.pdf"
            assert doc.status == "draft"
            assert doc.file_hash is not None
            assert len(doc.file_hash) == 64

    @pytest.mark.asyncio
    async def test_upload_kb_disabled(self):
        """测试上传到已停用的知识库"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_kb(status="disabled")
        )

        service = DocumentService(mock_db)
        with pytest.raises(BusinessStateError) as exc:
            await service.upload_document(
                tenant_id="t1", user_id="u1", knowledge_base_id="kb-001",
                filename="test.pdf", file_data=b"data", mime_type="application/pdf",
            )
        assert "停用" in exc.value.message

    @pytest.mark.asyncio
    async def test_upload_kb_not_found(self):
        """测试上传到不存在的知识库"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        service = DocumentService(mock_db)
        with pytest.raises(ResourceNotFoundError):
            await service.upload_document(
                tenant_id="t1", user_id="u1", knowledge_base_id="non-existent",
                filename="test.pdf", file_data=b"data", mime_type="application/pdf",
            )

    @pytest.mark.asyncio
    async def test_upload_invalid_extension(self):
        """测试上传不支持的文件类型"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(_make_kb())

        service = DocumentService(mock_db)
        with pytest.raises(ValidationError) as exc:
            await service.upload_document(
                tenant_id="t1", user_id="u1", knowledge_base_id="kb-001",
                filename="script.exe", file_data=b"data",
            )
        assert "不支持的文件类型" in exc.value.message

    @pytest.mark.asyncio
    async def test_upload_duplicate_file(self):
        """测试上传重复文件"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        kb_result = _make_mock_result(_make_kb())
        dup_result = _make_mock_result(_make_doc())  # 已存在的文档

        mock_db.execute.side_effect = [kb_result, dup_result]

        with patch("app.services.document.MinioStorageService"):
            service = DocumentService(mock_db)
            with pytest.raises(ValidationError) as exc:
                await service.upload_document(
                    tenant_id="t1", user_id="u1", knowledge_base_id="kb-001",
                    filename="test.pdf", file_data=b"same content",
                    mime_type="application/pdf",
                )
            assert "相同内容" in exc.value.message

    @pytest.mark.asyncio
    async def test_upload_storage_failure_rollback(self):
        """测试MinIO上传失败时回滚数据库"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        kb_result = _make_mock_result(_make_kb())
        dup_result = _make_mock_result(None)
        mock_db.execute.side_effect = [kb_result, dup_result]

        with patch("app.services.document.MinioStorageService") as mock_storage_cls:
            mock_storage = MagicMock()
            mock_storage.upload_file.side_effect = StorageError(
                message="MinIO连接失败",
                details={"error": "Connection refused"},
            )
            mock_storage_cls.return_value = mock_storage

            service = DocumentService(mock_db)
            with pytest.raises(StorageError):
                await service.upload_document(
                    tenant_id="t1", user_id="u1", knowledge_base_id="kb-001",
                    filename="test.pdf", file_data=b"data", mime_type="application/pdf",
                )

            # 验证回滚被调用
            mock_db.rollback.assert_called()


# =============================================================================
# 文档查询测试
# =============================================================================

class TestDocumentQuery:

    @pytest.mark.asyncio
    async def test_get_document_success(self):
        """测试获取文档详情"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(name="测试文档.pdf")
        )

        service = DocumentService(mock_db)
        doc = await service.get_document("doc-001", tenant_id="t1")

        assert doc.name == "测试文档.pdf"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self):
        """测试获取不存在的文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        service = DocumentService(mock_db)
        with pytest.raises(ResourceNotFoundError):
            await service.get_document("non-existent", tenant_id="t1")

    @pytest.mark.asyncio
    async def test_list_documents_with_filters(self):
        """测试带筛选条件的文档列表"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [_make_doc()]

        mock_db.execute.side_effect = [count_result, list_result]

        service = DocumentService(mock_db)
        params = DocumentListParams(
            knowledge_base_id="kb-001", status="published", keyword="手册"
        )
        items, total = await service.list_documents(
            "t1", PaginationParams(page=1, page_size=20), params
        )

        assert total == 1
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_get_chunk_count(self):
        """测试获取文档Chunk数量"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        mock_db.execute.return_value = count_result

        service = DocumentService(mock_db)
        count = await service.get_chunk_count("doc-001")

        assert count == 5


# =============================================================================
# 文档发布控制测试
# =============================================================================

class TestDocumentPublishControl:

    @pytest.mark.asyncio
    async def test_publish_success(self):
        """测试发布文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(status="pending_publish")
        )

        service = DocumentService(mock_db)
        doc = await service.publish_document("doc-001", tenant_id="t1")

        assert doc.status == "published"
        assert doc.published_at is not None

    @pytest.mark.asyncio
    async def test_publish_wrong_status(self):
        """测试发布非待发布状态的文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(status="draft")
        )

        service = DocumentService(mock_db)
        with pytest.raises(BusinessStateError):
            await service.publish_document("doc-001", tenant_id="t1")

    @pytest.mark.asyncio
    async def test_pause_success(self):
        """测试暂停已发布文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(status="published")
        )

        service = DocumentService(mock_db)
        doc = await service.pause_document("doc-001", tenant_id="t1")

        assert doc.status == "paused"

    @pytest.mark.asyncio
    async def test_pause_wrong_status(self):
        """测试暂停非已发布状态的文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(status="draft")
        )

        service = DocumentService(mock_db)
        with pytest.raises(BusinessStateError):
            await service.pause_document("doc-001", tenant_id="t1")

    @pytest.mark.asyncio
    async def test_offline_success(self):
        """测试下线已发布文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(status="published")
        )

        service = DocumentService(mock_db)
        doc = await service.offline_document("doc-001", tenant_id="t1")

        assert doc.status == "offline"

    @pytest.mark.asyncio
    async def test_offline_paused_document(self):
        """测试下线已暂停文档"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(status="paused")
        )

        service = DocumentService(mock_db)
        doc = await service.offline_document("doc-001", tenant_id="t1")

        assert doc.status == "offline"

    @pytest.mark.asyncio
    async def test_offline_wrong_status(self):
        """测试下线草稿文档（应失败）"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            _make_doc(status="draft")
        )

        service = DocumentService(mock_db)
        with pytest.raises(BusinessStateError):
            await service.offline_document("doc-001", tenant_id="t1")


# =============================================================================
# 版本管理测试
# =============================================================================

class TestVersionManagement:

    @pytest.mark.asyncio
    async def test_get_versions(self):
        """测试获取文档版本列表"""
        from app.services.document import DocumentService
        from app.models.document import DocumentVersion

        mock_db = AsyncMock()

        # 第一次调用：get_document验证
        doc_result = _make_mock_result(_make_doc())
        # 第二次调用：版本列表
        ver1 = DocumentVersion(
            id="ver-001", tenant_id="t1", document_id="doc-001",
            knowledge_base_id="kb-001", version=1, file_path="path/v1.pdf",
            file_size=1024, file_hash="h1", created_by="u1",
        )
        ver2 = DocumentVersion(
            id="ver-002", tenant_id="t1", document_id="doc-001",
            knowledge_base_id="kb-001", version=2, file_path="path/v2.pdf",
            file_size=2048, file_hash="h2", created_by="u1",
        )
        ver_result = MagicMock()
        ver_result.scalars.return_value.all.return_value = [ver2, ver1]

        mock_db.execute.side_effect = [doc_result, ver_result]

        service = DocumentService(mock_db)
        versions = await service.get_versions("doc-001", tenant_id="t1")

        assert len(versions) == 2
        assert versions[0].version == 2  # 按版本号降序，v2在前

    @pytest.mark.asyncio
    async def test_get_version_detail(self):
        """测试获取版本详情"""
        from app.services.document import DocumentService
        from app.models.document import DocumentVersion

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(
            DocumentVersion(
                id="ver-001", tenant_id="t1", document_id="doc-001",
                knowledge_base_id="kb-001", version=1, file_path="path/v1.pdf",
                file_size=1024, file_hash="hash123", created_by="u1",
            )
        )

        service = DocumentService(mock_db)
        ver = await service.get_version_detail("doc-001", "ver-001", tenant_id="t1")

        assert ver.version == 1
        assert ver.document_id == "doc-001"

    @pytest.mark.asyncio
    async def test_get_version_not_found(self):
        """测试获取不存在的版本"""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        service = DocumentService(mock_db)
        with pytest.raises(ResourceNotFoundError):
            await service.get_version_detail("doc-001", "non-existent", tenant_id="t1")
