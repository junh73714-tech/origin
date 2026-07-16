"""
文档模型单元测试

测试 KnowledgeBase、Document、DocumentVersion、DocumentChunk、
IndexTask、DocumentProcessLog 及权限模型的字段完整性和约束。
"""
import pytest
from datetime import datetime, timezone


# =============================================================================
# KnowledgeBase 模型测试
# =============================================================================

class TestKnowledgeBase:
    """知识库模型测试"""

    def test_create_knowledge_base_minimal(self):
        """测试创建知识库 -- 最少必填字段"""
        from app.models.document import KnowledgeBase

        kb = KnowledgeBase(
            id="kb-001",
            tenant_id="tenant-001",
            name="测试知识库",
            status="active",
            created_by="user-001",
        )
        assert kb.name == "测试知识库"
        assert kb.status == "active"

    def test_create_knowledge_base_full(self):
        """测试创建知识库 -- 全部字段"""
        from app.models.document import KnowledgeBase

        kb = KnowledgeBase(
            id="kb-002",
            tenant_id="tenant-001",
            name="完整知识库",
            description="这是一个测试知识库",
            icon="https://example.com/icon.png",
            is_public=True,
            status="active",
            business_domain="人力资源",
            settings={"language": "zh-CN"},
            document_count=10,
            chunk_count=100,
            created_by="user-001",
        )
        assert kb.business_domain == "人力资源"
        assert kb.settings == {"language": "zh-CN"}
        assert kb.document_count == 10
        assert kb.chunk_count == 100

    def test_knowledge_base_status_values(self):
        """测试知识库状态的有效值"""
        from app.models.document import KnowledgeBase

        # 启用状态
        kb_active = KnowledgeBase(
            id="kb-003", tenant_id="t1", name="启用", status="active", created_by="u1"
        )
        assert kb_active.status == "active"

        # 停用状态
        kb_disabled = KnowledgeBase(
            id="kb-004", tenant_id="t1", name="停用", status="disabled", created_by="u1"
        )
        assert kb_disabled.status == "disabled"

    def test_knowledge_base_repr(self):
        """测试知识库字符串表示"""
        from app.models.document import KnowledgeBase

        kb = KnowledgeBase(
            id="kb-005", tenant_id="t1", name="HR知识库", status="active", created_by="u1"
        )
        repr_str = repr(kb)
        assert "HR知识库" in repr_str
        assert "active" in repr_str

    def test_knowledge_base_table_name(self):
        """测试知识库表名"""
        from app.models.document import KnowledgeBase

        assert KnowledgeBase.__tablename__ == "knowledge_bases"


class TestKnowledgeBasePermission:
    """知识库权限模型测试"""

    def test_create_permission(self):
        """测试创建知识库权限"""
        from app.models.document import KnowledgeBasePermission

        perm = KnowledgeBasePermission(
            id="kp-001",
            tenant_id="tenant-001",
            knowledge_base_id="kb-001",
            principal_type="user",
            principal_id="user-001",
            permission_type="read",
            is_deny=False,
            created_by="admin",
        )
        assert perm.principal_type == "user"
        assert perm.permission_type == "read"
        assert perm.is_deny is False

    def test_create_deny_permission(self):
        """测试创建显式拒绝权限"""
        from app.models.document import KnowledgeBasePermission

        perm = KnowledgeBasePermission(
            id="kp-002",
            tenant_id="tenant-001",
            knowledge_base_id="kb-001",
            principal_type="user",
            principal_id="user-002",
            permission_type="read",
            is_deny=True,
            created_by="admin",
        )
        assert perm.is_deny is True

    def test_permission_with_time_range(self):
        """测试带时间范围的权限"""
        from app.models.document import KnowledgeBasePermission

        now = datetime.now(timezone.utc)
        perm = KnowledgeBasePermission(
            id="kp-003",
            tenant_id="tenant-001",
            knowledge_base_id="kb-001",
            principal_type="role",
            principal_id="role-001",
            permission_type="write",
            effective_time=now,
            expiration_time=now,
            created_by="admin",
        )
        assert perm.effective_time is not None
        assert perm.expiration_time is not None

    def test_permission_table_name(self):
        """测试权限表名"""
        from app.models.document import KnowledgeBasePermission

        assert KnowledgeBasePermission.__tablename__ == "knowledge_base_permissions"


# =============================================================================
# Document 模型测试
# =============================================================================

class TestDocument:
    """文档模型测试"""

    def test_create_document_minimal(self):
        """测试创建文档 -- 最少必填字段"""
        from app.models.document import Document

        doc = Document(
            id="doc-001",
            tenant_id="tenant-001",
            knowledge_base_id="kb-001",
            name="员工手册v2.pdf",
            original_filename="员工手册v2.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            file_size=1024000,
            file_hash="abc123def456",
            file_path="tenant-001/kb-001/doc-001/v1/abc123.pdf",
            status="draft",
            current_version=1,
            created_by="user-001",
        )
        assert doc.status == "draft"
        assert doc.current_version == 1
        assert doc.file_hash == "abc123def456"
        assert doc.mime_type == "application/pdf"

    def test_document_status_values(self):
        """测试文档状态的有效值（完整状态机覆盖）"""
        from app.models.document import Document

        valid_statuses = [
            "draft", "processing", "failed", "pending_review",
            "pending_publish", "published", "paused", "expired",
            "offline", "archived",
        ]
        for status in valid_statuses:
            doc = Document(
                id=f"doc-{status}",
                tenant_id="t1",
                knowledge_base_id="kb-001",
                name=f"test_{status}.pdf",
                original_filename=f"test_{status}.pdf",
                file_type="pdf",
                mime_type="application/pdf",
                file_size=1000,
                file_hash=f"hash_{status}",
                file_path=f"path/{status}",
                status=status,
                created_by="u1",
            )
            assert doc.status == status

    def test_document_with_processing_error(self):
        """测试处理失败的文档"""
        from app.models.document import Document

        doc = Document(
            id="doc-failed",
            tenant_id="t1",
            knowledge_base_id="kb-001",
            name="bad.pdf",
            original_filename="bad.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            file_size=100,
            file_hash="badhash",
            file_path="path/bad.pdf",
            status="failed",
            processing_error="PDF解析失败: 文件损坏",
            created_by="u1",
        )
        assert doc.status == "failed"
        assert "PDF解析失败" in doc.processing_error

    def test_document_with_published_at(self):
        """测试已发布文档的发布时间"""
        from app.models.document import Document

        published_time = datetime.now(timezone.utc)
        doc = Document(
            id="doc-pub",
            tenant_id="t1",
            knowledge_base_id="kb-001",
            name="published.pdf",
            original_filename="published.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            file_size=1000,
            file_hash="pubhash",
            file_path="path/pub.pdf",
            status="published",
            published_at=published_time,
            page_count=50,
            char_count=100000,
            token_count=30000,
            created_by="u1",
        )
        assert doc.status == "published"
        assert doc.published_at == published_time
        assert doc.page_count == 50
        assert doc.char_count == 100000
        assert doc.token_count == 30000

    def test_document_table_name(self):
        """测试文档表名"""
        from app.models.document import Document

        assert Document.__tablename__ == "documents"

    def test_document_repr(self):
        """测试文档字符串表示"""
        from app.models.document import Document

        doc = Document(
            id="doc-r", tenant_id="t1", knowledge_base_id="kb-001",
            name="test.txt", original_filename="test.txt", file_type="txt",
            mime_type="text/plain", file_size=100, file_hash="hash",
            file_path="path/test.txt", status="published", created_by="u1",
        )
        repr_str = repr(doc)
        assert "test.txt" in repr_str
        assert "published" in repr_str


class TestDocumentPermission:
    """文档权限模型测试"""

    def test_create_document_permission(self):
        """测试创建文档权限"""
        from app.models.document import DocumentPermission

        perm = DocumentPermission(
            id="dp-001",
            tenant_id="t1",
            document_id="doc-001",
            principal_type="department",
            principal_id="dept-hr",
            permission_type="read",
            is_deny=False,
            created_by="admin",
        )
        assert perm.principal_type == "department"
        assert perm.is_deny is False

    def test_document_permission_table_name(self):
        """测试文档权限表名"""
        from app.models.document import DocumentPermission

        assert DocumentPermission.__tablename__ == "document_permissions"


# =============================================================================
# DocumentVersion 模型测试
# =============================================================================

class TestDocumentVersion:
    """文档版本模型测试"""

    def test_create_version_minimal(self):
        """测试创建文档版本"""
        from app.models.document import DocumentVersion

        ver = DocumentVersion(
            id="ver-001",
            tenant_id="t1",
            document_id="doc-001",
            knowledge_base_id="kb-001",
            version=1,
            file_path="path/v1.pdf",
            file_size=1024000,
            file_hash="hash123",
            is_current_version=False,
            publish_status="draft",
            created_by="u1",
        )
        assert ver.version == 1
        assert ver.is_current_version is False
        assert ver.publish_status == "draft"

    def test_version_is_current(self):
        """测试当前版本标记"""
        from app.models.document import DocumentVersion

        ver = DocumentVersion(
            id="ver-002",
            tenant_id="t1",
            document_id="doc-001",
            knowledge_base_id="kb-001",
            version=2,
            file_path="path/v2.pdf",
            file_size=2048000,
            file_hash="hash456",
            previous_version=1,
            is_current_version=True,
            change_summary="更新了第三章内容",
            publish_status="published",
            created_by="u1",
        )
        assert ver.is_current_version is True
        assert ver.previous_version == 1
        assert ver.change_summary == "更新了第三章内容"
        assert ver.publish_status == "published"

    def test_version_publish_status_values(self):
        """测试版本发布状态的有效值"""
        from app.models.document import DocumentVersion

        statuses = ["draft", "processing", "failed", "pending_review",
                     "pending_publish", "published", "offline", "archived"]
        for i, status in enumerate(statuses):
            ver = DocumentVersion(
                id=f"ver-s{i}",
                tenant_id="t1",
                document_id="doc-001",
                knowledge_base_id="kb-001",
                version=i + 1,
                file_path=f"path/v{i}.pdf",
                file_size=1000,
                file_hash=f"hash{i}",
                publish_status=status,
                created_by="u1",
            )
            assert ver.publish_status == status

    def test_version_with_time_range(self):
        """测试带时间范围的版本"""
        from app.models.document import DocumentVersion

        now = datetime.now(timezone.utc)
        ver = DocumentVersion(
            id="ver-time",
            tenant_id="t1",
            document_id="doc-001",
            knowledge_base_id="kb-001",
            version=3,
            file_path="path/v3.pdf",
            file_size=1000,
            file_hash="hash",
            effective_time=now,
            expiration_time=now,
            published_at=now,
            created_by="u1",
        )
        assert ver.effective_time == now
        assert ver.expiration_time == now
        assert ver.published_at == now

    def test_version_table_name(self):
        """测试版本表名"""
        from app.models.document import DocumentVersion

        assert DocumentVersion.__tablename__ == "document_versions"


# =============================================================================
# DocumentChunk 模型测试
# =============================================================================

class TestDocumentChunk:
    """文档Chunk模型测试"""

    def test_create_chunk_minimal(self):
        """测试创建Chunk -- 最少必填字段"""
        from app.models.document import DocumentChunk

        chunk = DocumentChunk(
            id="chunk-001",
            tenant_id="t1",
            knowledge_base_id="kb-001",
            document_id="doc-001",
            document_version_id="ver-001",
            chunk_no=1,
            raw_text="这是原始文本内容。",
            clean_text="这是清洗后文本内容。",
            content_hash="chash123",
            status="active",
            index_status="pending",
            created_by="u1",
        )
        assert chunk.chunk_no == 1
        assert chunk.status == "active"
        assert chunk.index_status == "pending"

    def test_create_chunk_full(self):
        """测试创建Chunk -- 全部字段"""
        from app.models.document import DocumentChunk

        now = datetime.now(timezone.utc)
        chunk = DocumentChunk(
            id="chunk-002",
            tenant_id="t1",
            knowledge_base_id="kb-001",
            document_id="doc-001",
            document_version_id="ver-001",
            chunk_no=5,
            title_path="第一章 > 第一节 > 概述",
            page_start=10,
            page_end=11,
            source_offset=5000,
            raw_text="原始文本\n包含换行",
            clean_text="清洗后文本包含换行",
            content_hash="hash_full_001",
            token_count=150,
            chunk_metadata={"keywords": ["测试", "文档"]},
            permission_metadata={
                "scope_hash": "abc123",
                "allow_roles": ["reader"],
            },
            effective_time=now,
            expiration_time=now,
            status="active",
            index_status="indexed",
            created_by="u1",
        )
        assert chunk.chunk_no == 5
        assert chunk.title_path == "第一章 > 第一节 > 概述"
        assert chunk.page_start == 10
        assert chunk.page_end == 11
        assert chunk.source_offset == 5000
        assert chunk.raw_text == "原始文本\n包含换行"
        assert chunk.clean_text == "清洗后文本包含换行"
        assert chunk.token_count == 150
        assert chunk.chunk_metadata == {"keywords": ["测试", "文档"]}
        assert chunk.permission_metadata["scope_hash"] == "abc123"
        assert chunk.status == "active"
        assert chunk.index_status == "indexed"

    def test_chunk_title_path_none(self):
        """测试无标题路径的Chunk"""
        from app.models.document import DocumentChunk

        chunk = DocumentChunk(
            id="chunk-003", tenant_id="t1", knowledge_base_id="kb-001",
            document_id="doc-001", document_version_id="ver-001",
            chunk_no=1, raw_text="text", clean_text="text",
            content_hash="hash", created_by="u1",
        )
        assert chunk.title_path is None
        assert chunk.page_start is None
        assert chunk.page_end is None

    def test_chunk_status_values(self):
        """测试Chunk状态的有效值"""
        from app.models.document import DocumentChunk

        for status in ["active", "outdated", "deleted"]:
            chunk = DocumentChunk(
                id=f"chunk-{status}", tenant_id="t1", knowledge_base_id="kb-001",
                document_id="doc-001", document_version_id="ver-001",
                chunk_no=1, raw_text="text", clean_text="text",
                content_hash=f"hash_{status}", status=status, created_by="u1",
            )
            assert chunk.status == status

    def test_chunk_index_status_values(self):
        """测试Chunk索引状态的有效值"""
        from app.models.document import DocumentChunk

        for idx_status in ["pending", "indexing", "indexed", "failed"]:
            chunk = DocumentChunk(
                id=f"chunk-idx-{idx_status}", tenant_id="t1", knowledge_base_id="kb-001",
                document_id="doc-001", document_version_id="ver-001",
                chunk_no=1, raw_text="text", clean_text="text",
                content_hash=f"hash_{idx_status}", index_status=idx_status, created_by="u1",
            )
            assert chunk.index_status == idx_status

    def test_chunk_table_name(self):
        """测试Chunk表名"""
        from app.models.document import DocumentChunk

        assert DocumentChunk.__tablename__ == "document_chunks"

    def test_chunk_repr(self):
        """测试Chunk字符串表示"""
        from app.models.document import DocumentChunk

        chunk = DocumentChunk(
            id="chunk-r", tenant_id="t1", knowledge_base_id="kb-001",
            document_id="doc-001", document_version_id="ver-001",
            chunk_no=3, raw_text="text", clean_text="text",
            content_hash="hash", created_by="u1",
        )
        repr_str = repr(chunk)
        assert "doc-001" in repr_str
        assert "ver-001" in repr_str


# =============================================================================
# IndexTask 模型测试
# =============================================================================

class TestIndexTask:
    """索引任务模型测试"""

    def test_create_index_task_minimal(self):
        """测试创建索引任务"""
        from app.models.document import IndexTask

        task = IndexTask(
            id="task-001",
            tenant_id="t1",
            document_id="doc-001",
            document_version_id="ver-001",
            task_type="create",
            target="both",
            idempotent_key="idx_doc-001_ver-001_create",
            status="pending",
            retry_count=0,
            max_retries=3,
            progress=0,
            created_by="system",
        )
        assert task.task_type == "create"
        assert task.target == "both"
        assert task.status == "pending"

    def test_index_task_types(self):
        """测试索引任务类型"""
        from app.models.document import IndexTask

        task_types = ["create", "update", "delete", "rebuild", "consistency_check"]
        for i, ttype in enumerate(task_types):
            task = IndexTask(
                id=f"task-{ttype}",
                tenant_id="t1",
                document_id="doc-001",
                document_version_id="ver-001",
                task_type=ttype,
                idempotent_key=f"key_{ttype}_{i}",
                created_by="system",
            )
            assert task.task_type == ttype

    def test_index_task_targets(self):
        """测试索引目标"""
        from app.models.document import IndexTask

        for target in ["opensearch", "pgvector", "both"]:
            task = IndexTask(
                id=f"task-t-{target}",
                tenant_id="t1",
                document_id="doc-001",
                document_version_id="ver-001",
                task_type="create",
                target=target,
                idempotent_key=f"key_{target}",
                created_by="system",
            )
            assert task.target == target

    def test_index_task_with_chunk(self):
        """测试单Chunk索引任务"""
        from app.models.document import IndexTask

        task = IndexTask(
            id="task-chunk",
            tenant_id="t1",
            document_id="doc-001",
            document_version_id="ver-001",
            chunk_id="chunk-001",
            task_type="update",
            idempotent_key="key_chunk_001",
            created_by="system",
        )
        assert task.chunk_id == "chunk-001"

    def test_index_task_failed_with_retry(self):
        """测试失败可重试的索引任务"""
        from app.models.document import IndexTask

        task = IndexTask(
            id="task-failed",
            tenant_id="t1",
            document_id="doc-001",
            document_version_id="ver-001",
            task_type="create",
            idempotent_key="key_failed",
            status="failed",
            retry_count=2,
            max_retries=3,
            error_message="OpenSearch连接超时",
            created_by="system",
        )
        assert task.status == "failed"
        assert task.retry_count == 2
        assert task.retry_count < task.max_retries
        assert "OpenSearch" in task.error_message

    def test_index_task_completed(self):
        """测试已完成的索引任务"""
        from app.models.document import IndexTask

        now = datetime.now(timezone.utc)
        task = IndexTask(
            id="task-done",
            tenant_id="t1",
            document_id="doc-001",
            document_version_id="ver-001",
            task_type="create",
            idempotent_key="key_done",
            status="completed",
            progress=100,
            total_chunks=50,
            indexed_chunks=50,
            started_at=now,
            completed_at=now,
            created_by="system",
        )
        assert task.status == "completed"
        assert task.progress == 100
        assert task.indexed_chunks == task.total_chunks

    def test_index_task_unique_idempotent_key(self):
        """测试幂等键唯一性"""
        from app.models.document import IndexTask

        task = IndexTask(
            id="task-ikey",
            tenant_id="t1",
            document_id="doc-001",
            document_version_id="ver-001",
            task_type="create",
            idempotent_key="unique_key_12345",
            created_by="system",
        )
        assert task.idempotent_key == "unique_key_12345"

    def test_index_task_table_name(self):
        """测试索引任务表名"""
        from app.models.document import IndexTask

        assert IndexTask.__tablename__ == "index_tasks"


# =============================================================================
# DocumentProcessLog 模型测试
# =============================================================================

class TestDocumentProcessLog:
    """文档处理日志模型测试"""

    def test_create_process_log(self):
        """测试创建处理日志"""
        from app.models.document import DocumentProcessLog

        log = DocumentProcessLog(
            id="log-001",
            tenant_id="t1",
            document_id="doc-001",
            document_version_id="ver-001",
            stage="parse",
            status="completed",
            progress=100,
            created_by="system",
        )
        assert log.stage == "parse"
        assert log.status == "completed"
        assert log.progress == 100

    def test_process_log_stages(self):
        """测试处理阶段的有效值"""
        from app.models.document import DocumentProcessLog

        stages = [
            "upload", "parse", "clean", "split", "embed",
            "index_opensearch", "index_pgvector", "publish",
        ]
        for stage in stages:
            log = DocumentProcessLog(
                id=f"log-{stage}",
                tenant_id="t1",
                document_id="doc-001",
                stage=stage,
                status="pending",
                created_by="system",
            )
            assert log.stage == stage

    def test_process_log_error(self):
        """测试处理失败日志"""
        from app.models.document import DocumentProcessLog

        log = DocumentProcessLog(
            id="log-err",
            tenant_id="t1",
            document_id="doc-001",
            document_version_id="ver-001",
            stage="parse",
            status="failed",
            progress=30,
            error_type="ParseError",
            error_message="PDF文件第5页解析失败: 无法识别的编码",
            error_stack="Traceback...",
            stage_metadata={"failed_page": 5},
            created_by="system",
        )
        assert log.status == "failed"
        assert log.error_type == "ParseError"
        assert "第5页" in log.error_message
        assert log.stage_metadata == {"failed_page": 5}

    def test_process_log_without_version(self):
        """测试无版本关联的处理日志"""
        from app.models.document import DocumentProcessLog

        log = DocumentProcessLog(
            id="log-nover",
            tenant_id="t1",
            document_id="doc-001",
            stage="upload",
            status="completed",
            created_by="system",
        )
        assert log.document_version_id is None

    def test_process_log_table_name(self):
        """测试处理日志表名"""
        from app.models.document import DocumentProcessLog

        assert DocumentProcessLog.__tablename__ == "document_process_logs"


# =============================================================================
# 模型关系测试
# =============================================================================

class TestModelRelationships:
    """模型关系测试"""

    def test_knowledge_base_document_relationship(self):
        """测试知识库与文档的一对多关系"""
        from app.models.document import KnowledgeBase, Document

        assert hasattr(KnowledgeBase, "documents")
        assert hasattr(Document, "knowledge_base")

    def test_document_version_relationship(self):
        """测试文档与版本的一对多关系"""
        from app.models.document import Document, DocumentVersion

        assert hasattr(Document, "versions")
        assert hasattr(DocumentVersion, "document")

    def test_document_chunk_relationship(self):
        """测试文档与Chunk的一对多关系"""
        from app.models.document import Document, DocumentChunk

        assert hasattr(Document, "chunks")
        assert hasattr(DocumentChunk, "document")

    def test_version_chunk_relationship(self):
        """测试版本与Chunk的一对多关系"""
        from app.models.document import DocumentVersion, DocumentChunk

        assert hasattr(DocumentVersion, "chunks")
        assert hasattr(DocumentChunk, "document_version")

    def test_document_permission_relationship(self):
        """测试文档与权限的一对多关系"""
        from app.models.document import Document, DocumentPermission

        assert hasattr(Document, "permissions")
        assert hasattr(DocumentPermission, "document")

    def test_knowledge_base_permission_relationship(self):
        """测试知识库与权限的一对多关系"""
        from app.models.document import KnowledgeBase, KnowledgeBasePermission

        assert hasattr(KnowledgeBase, "permissions")
        assert hasattr(KnowledgeBasePermission, "knowledge_base")

    def test_document_process_log_relationship(self):
        """测试文档与处理日志的一对多关系"""
        from app.models.document import Document, DocumentProcessLog

        assert hasattr(Document, "process_logs")
        assert hasattr(DocumentProcessLog, "document")


# =============================================================================
# BaseModel 继承测试
# =============================================================================

class TestModelInheritance:
    """模型继承测试"""

    def test_knowledge_base_inherits_base_model_fields(self):
        """测试知识库继承BaseModel的公共字段"""
        from app.models.document import KnowledgeBase

        kb = KnowledgeBase(
            id="kb-inh", tenant_id="t1", name="test", created_by="u1"
        )
        assert hasattr(kb, "id")
        assert hasattr(kb, "tenant_id")
        assert hasattr(kb, "created_at")
        assert hasattr(kb, "updated_at")
        assert hasattr(kb, "created_by")
        assert hasattr(kb, "updated_by")

    def test_document_chunk_has_all_required_fields(self):
        """测试DocumentChunk包含任务书要求的所有必填字段"""
        from app.models.document import DocumentChunk

        required_fields = [
            "tenant_id", "knowledge_base_id", "document_id", "document_version_id",
            "chunk_no", "title_path", "page_start", "page_end", "source_offset",
            "raw_text", "clean_text", "token_count", "metadata",
            "permission_metadata", "effective_time", "expiration_time", "status",
        ]
        for field in required_fields:
            assert hasattr(DocumentChunk, field), f"DocumentChunk缺少字段: {field}"

    def test_index_task_has_all_required_fields(self):
        """测试IndexTask包含任务书要求的所有必填字段"""
        from app.models.document import IndexTask

        required_fields = [
            "task_type", "target", "document_version_id", "chunk_id",
            "idempotent_key", "status", "retry_count", "error_message",
            "created_at", "completed_at",
        ]
        for field in required_fields:
            assert hasattr(IndexTask, field), f"IndexTask缺少字段: {field}"
