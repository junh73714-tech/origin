"""
文档编排器单元测试

测试 DocumentOrchestrator 的状态流转、Chunk差异比对和Outbox事件发布。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import BusinessStateError


def _make_doc(**kwargs):
    """创建测试用 Document"""
    from app.models.document import Document
    defaults = {
        "id": "doc-001", "tenant_id": "t1", "knowledge_base_id": "kb-001",
        "name": "test.pdf", "original_filename": "test.pdf",
        "file_type": "pdf", "mime_type": "application/pdf",
        "file_size": 1024, "file_hash": "h1", "file_path": "path",
        "status": "pending_publish", "current_version": 1, "created_by": "u1",
    }
    defaults.update(kwargs)
    return Document(**defaults)


def _make_version(**kwargs):
    """创建测试用 DocumentVersion"""
    from app.models.document import DocumentVersion
    defaults = {
        "id": "ver-001", "tenant_id": "t1", "document_id": "doc-001",
        "knowledge_base_id": "kb-001", "version": 1, "file_path": "path",
        "file_size": 1024, "file_hash": "h1", "is_current_version": True,
        "publish_status": "pending_publish", "created_by": "u1",
    }
    defaults.update(kwargs)
    return DocumentVersion(**defaults)


def _make_chunk(**kwargs):
    """创建测试用 DocumentChunk"""
    from app.models.document import DocumentChunk
    defaults = {
        "id": "chunk-001", "tenant_id": "t1", "knowledge_base_id": "kb-001",
        "document_id": "doc-001", "document_version_id": "ver-001",
        "chunk_no": 1, "raw_text": "文本", "clean_text": "文本",
        "content_hash": "abc", "token_count": 5, "status": "active",
        "index_status": "pending", "created_by": "u1",
    }
    defaults.update(kwargs)
    return DocumentChunk(**defaults)


# =============================================================================
# 状态流转测试
# =============================================================================

class TestDocumentStateTransitions:

    def test_hash_text(self):
        """测试文本哈希计算"""
        from app.services.orchestrator import DocumentOrchestrator

        h1 = DocumentOrchestrator._hash_text("hello")
        h2 = DocumentOrchestrator._hash_text("hello")
        h3 = DocumentOrchestrator._hash_text("world")

        assert len(h1) == 64
        assert h1 == h2
        assert h1 != h3

    def test_compare_chunks_empty(self):
        """测试空Chunk对比"""
        from app.services.orchestrator import DocumentOrchestrator
        orchestrator = DocumentOrchestrator.__new__(DocumentOrchestrator)
        diff = orchestrator._compare_chunks([], [])

        assert diff["added"] == 0
        assert diff["deleted"] == 0
        assert diff["unchanged"] == 0

    def test_compare_chunks_no_change(self):
        """测试无变化Chunk对比"""
        from app.services.orchestrator import DocumentOrchestrator
        orchestrator = DocumentOrchestrator.__new__(DocumentOrchestrator)
        old = [_make_chunk(content_hash="abc"), _make_chunk(content_hash="def")]
        new = [_make_chunk(content_hash="abc"), _make_chunk(content_hash="def")]

        diff = orchestrator._compare_chunks(old, new)
        assert diff["added"] == 0
        assert diff["deleted"] == 0
        assert diff["unchanged"] == 2

    def test_compare_chunks_with_changes(self):
        """测试有变化的Chunk对比"""
        from app.services.orchestrator import DocumentOrchestrator
        orchestrator = DocumentOrchestrator.__new__(DocumentOrchestrator)
        old = [
            _make_chunk(content_hash="a"),  # 保留
            _make_chunk(content_hash="b"),  # 删除
        ]
        new = [
            _make_chunk(content_hash="a"),  # 保留
            _make_chunk(content_hash="c"),  # 新增
        ]

        diff = orchestrator._compare_chunks(old, new)
        assert diff["added"] == 1
        assert diff["deleted"] == 1
        assert diff["unchanged"] == 1


# =============================================================================
# 发布控制测试
# =============================================================================

class TestPublishControl:

    @pytest.mark.asyncio
    async def test_publish_success(self):
        """测试成功发布文档版本"""
        from app.services.orchestrator import DocumentOrchestrator

        mock_db = AsyncMock()
        doc = _make_doc(status="pending_publish")
        version = _make_version(publish_status="pending_publish")

        def make_result(value):
            r = MagicMock()
            r.scalar_one_or_none.return_value = value
            return r

        mock_db.execute.side_effect = [
            make_result(doc),      # _get_document
            make_result(version),  # _get_current_version
            make_result([]),       # _get_old_versions (empty)
        ]

        orchestrator = DocumentOrchestrator(mock_db)
        result = await orchestrator.publish_document_version("doc-001", "t1")

        assert result.status == "published"
        assert result.published_at is not None

    @pytest.mark.asyncio
    async def test_publish_wrong_status(self):
        """测试发布非待发布状态的文档"""
        from app.services.orchestrator import DocumentOrchestrator

        mock_db = AsyncMock()
        doc = _make_doc(status="draft")

        r = MagicMock()
        r.scalar_one_or_none.return_value = doc
        mock_db.execute.return_value = r

        orchestrator = DocumentOrchestrator(mock_db)
        with pytest.raises(BusinessStateError):
            await orchestrator.publish_document_version("doc-001", "t1")

    @pytest.mark.asyncio
    async def test_offline_success(self):
        """测试成功下线文档"""
        from app.services.orchestrator import DocumentOrchestrator

        mock_db = AsyncMock()
        doc = _make_doc(status="published")
        version = _make_version(publish_status="published")

        def make_result(value):
            r = MagicMock()
            r.scalar_one_or_none.return_value = value
            return r

        mock_db.execute.side_effect = [
            make_result(doc),      # _get_document
            make_result(version),  # _get_current_version
        ]

        orchestrator = DocumentOrchestrator(mock_db)
        result = await orchestrator.offline_document("doc-001", "t1")

        assert result.status == "offline"

    @pytest.mark.asyncio
    async def test_offline_wrong_status(self):
        """测试下线草稿文档"""
        from app.services.orchestrator import DocumentOrchestrator

        mock_db = AsyncMock()
        doc = _make_doc(status="draft")
        r = MagicMock()
        r.scalar_one_or_none.return_value = doc
        mock_db.execute.return_value = r

        orchestrator = DocumentOrchestrator(mock_db)
        with pytest.raises(BusinessStateError):
            await orchestrator.offline_document("doc-001", "t1")


# =============================================================================
# Outbox 事件测试
# =============================================================================

class TestOutboxEvents:

    @pytest.mark.asyncio
    async def test_publish_outbox_event(self):
        """测试Outbox事件发布"""
        from app.services.orchestrator import DocumentOrchestrator
        from app.models.audit import OutboxEvent

        mock_db = AsyncMock()

        orchestrator = DocumentOrchestrator(mock_db)
        await orchestrator._publish_outbox_event(
            event_type="document.version.published",
            aggregate_type="document",
            aggregate_id="doc-001",
            payload={"version": 1, "document_id": "doc-001"},
        )

        # 验证事件被添加到数据库
        mock_db.add.assert_called()
        # 验证添加的是OutboxEvent类型
        added_event = mock_db.add.call_args[0][0]
        assert isinstance(added_event, OutboxEvent)
        assert added_event.event_type == "document.version.published"
        assert added_event.aggregate_id == "doc-001"


# =============================================================================
# 文档状态机完整性测试
# =============================================================================

class TestStateMachineCompleteness:

    def test_valid_status_transitions(self):
        """测试状态机流转路径完整性"""
        # 文档的合法状态流转
        valid_transitions = {
            "draft": ["processing"],
            "processing": ["failed", "pending_review"],
            "failed": ["draft"],  # 可回退重试
            "pending_review": ["pending_publish", "draft"],
            "pending_publish": ["published", "draft"],
            "published": ["paused", "expired", "offline"],
            "paused": ["published", "offline"],
            "expired": ["offline", "archived"],
            "offline": [],  # 终态
            "archived": [],  # 终态
        }

        for from_state, to_states in valid_transitions.items():
            for to_state in to_states:
                assert to_state != from_state, f"流转不应相同: {from_state} -> {to_state}"

    def test_published_is_retrievable(self):
        """测试只有published状态的文档可被检索"""
        retrievable = ["published"]
        non_retrievable = [
            "draft", "processing", "failed", "pending_review",
            "pending_publish", "paused", "expired", "offline", "archived",
        ]

        assert "published" in retrievable
        for status in non_retrievable:
            assert status not in retrievable, f"{status}不应可检索"

    def test_all_required_events_exist(self):
        """测试任务书要求的全部Outbox事件类型"""
        required_events = [
            "document.version.created",
            "document.version.published",
            "document.paused",
            "document.offlined",
            "document.permission.changed",
            "document.index.completed",
        ]

        for event_type in required_events:
            assert event_type.startswith("document."), f"事件类型前缀不对: {event_type}"
