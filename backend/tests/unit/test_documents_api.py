"""
文档 API 端点测试

Mock Service 层，测试 API 路由和响应格式。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.document import Document


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db):
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_doc(**kwargs):
    """创建完整 Document 实例"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    doc = Document(
        id=kwargs.get("id", "doc-001"),
        tenant_id=kwargs.get("tenant_id", "default"),
        knowledge_base_id=kwargs.get("knowledge_base_id", "kb-001"),
        name=kwargs.get("name", "test.pdf"),
        original_filename=kwargs.get("original_filename", "test.pdf"),
        file_type=kwargs.get("file_type", "pdf"),
        mime_type=kwargs.get("mime_type", "application/pdf"),
        file_size=kwargs.get("file_size", 1024),
        file_hash=kwargs.get("file_hash", "abc123"),
        file_path=kwargs.get("file_path", "path/key.pdf"),
        status=kwargs.get("status", "draft"),
        current_version=kwargs.get("current_version", 1),
        chunk_count=kwargs.get("chunk_count", 0),
        created_by=kwargs.get("created_by", "system"),
    )
    doc.created_at = kwargs.get("created_at", now)
    doc.updated_at = kwargs.get("updated_at", now)
    doc.page_count = kwargs.get("page_count", None)
    doc.char_count = kwargs.get("char_count", None)
    doc.token_count = kwargs.get("token_count", None)
    doc.processing_error = kwargs.get("processing_error", None)
    doc.published_at = kwargs.get("published_at", None)
    doc.doc_metadata = kwargs.get("doc_metadata", None)
    doc.updated_by = kwargs.get("updated_by", None)
    return doc


# =============================================================================
# 上传
# =============================================================================

class TestDocumentUpload:

    def test_upload_success(self, client, mock_db):
        doc = _make_doc(name="test.pdf", status="draft")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.upload_document = AsyncMock(return_value=doc)

            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", b"fake pdf", "application/pdf")},
                data={"knowledge_base_id": "kb-001"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "test.pdf"

    def test_upload_no_file(self, client, mock_db):
        response = client.post(
            "/api/v1/documents/upload",
            data={"knowledge_base_id": "kb-001"},
        )
        assert response.status_code == 422

    def test_batch_upload(self, client, mock_db):
        doc1 = _make_doc(id="d1", name="doc1.pdf")
        doc2 = _make_doc(id="d2", name="doc2.pdf")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.upload_document = AsyncMock(side_effect=[doc1, doc2])

            response = client.post(
                "/api/v1/documents/batch-upload",
                files=[
                    ("files", ("doc1.pdf", b"c1", "application/pdf")),
                    ("files", ("doc2.pdf", b"c2", "application/pdf")),
                ],
                data={"knowledge_base_id": "kb-001"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 2
        assert data["data"]["success"] == 2


# =============================================================================
# 查询
# =============================================================================

class TestDocumentQuery:

    def test_list(self, client, mock_db):
        doc = _make_doc(name="员工手册.pdf")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_documents = AsyncMock(return_value=([doc], 1))

            response = client.get("/api/v1/documents")

        assert response.status_code == 200
        assert response.json()["data"]["total"] == 1

    def test_list_with_filters(self, client, mock_db):
        doc = _make_doc(status="published")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.list_documents = AsyncMock(return_value=([doc], 1))

            response = client.get(
                "/api/v1/documents?knowledge_base_id=kb-001&status=published&keyword=手册"
            )

        assert response.status_code == 200

    def test_detail(self, client, mock_db):
        doc = _make_doc(name="员工手册.pdf", status="published")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_document = AsyncMock(return_value=doc)
            mock_svc.get_chunk_count = AsyncMock(return_value=5)

            response = client.get("/api/v1/documents/doc-001")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "员工手册.pdf"
        assert data["data"]["chunk_count"] == 5

    def test_not_found(self, client, mock_db):
        from app.core.exceptions import ResourceNotFoundError
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_document = AsyncMock(
                side_effect=ResourceNotFoundError("文档", "x")
            )
            response = client.get("/api/v1/documents/non-existent")

        assert response.status_code == 404


# =============================================================================
# 发布控制
# =============================================================================

class TestDocumentPublishControl:

    def test_publish(self, client, mock_db):
        doc = _make_doc(status="published")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.publish_document = AsyncMock(return_value=doc)

            response = client.patch("/api/v1/documents/doc-001/publish")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "published"

    def test_pause(self, client, mock_db):
        doc = _make_doc(status="paused")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.pause_document = AsyncMock(return_value=doc)

            response = client.patch("/api/v1/documents/doc-001/pause")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "paused"

    def test_offline(self, client, mock_db):
        doc = _make_doc(status="offline")
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.offline_document = AsyncMock(return_value=doc)

            response = client.patch("/api/v1/documents/doc-001/offline")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "offline"


# =============================================================================
# 版本管理
# =============================================================================

class TestVersionManagement:

    def test_list_versions(self, client, mock_db):
        from app.models.document import DocumentVersion
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        v1 = DocumentVersion(
            id="v1", tenant_id="default", document_id="doc-001",
            knowledge_base_id="kb-001", version=1, file_path="p/v1.pdf",
            file_size=100, file_hash="h1", is_current_version=False,
            publish_status="published", created_by="system",
        )
        v1.created_at = now
        v2 = DocumentVersion(
            id="v2", tenant_id="default", document_id="doc-001",
            knowledge_base_id="kb-001", version=2, file_path="p/v2.pdf",
            file_size=200, file_hash="h2", is_current_version=True,
            publish_status="published", created_by="system",
        )
        v2.created_at = now
        with patch("app.api.documents.DocumentService") as MockSvc:
            mock_svc = MockSvc.return_value
            mock_svc.get_versions = AsyncMock(return_value=[v2, v1])

            response = client.get("/api/v1/documents/doc-001/versions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["version"] == 2
