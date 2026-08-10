"""
Chunk API 端点测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
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


def _make_chunk(**kwargs):
    """创建完整 DocumentChunk 实例"""
    from app.models.document import DocumentChunk
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    defaults = {
        "id": "chunk-001", "tenant_id": "default",
        "knowledge_base_id": "kb-001", "document_id": "doc-001",
        "document_version_id": "ver-001", "chunk_no": 1,
        "raw_text": "原始文本", "clean_text": "清洗文本",
        "content_hash": "abc", "token_count": 5,
        "status": "active", "index_status": "indexed",
        "created_by": "system",
    }
    defaults.update(kwargs)
    chunk = DocumentChunk(**defaults)
    chunk.created_at = kwargs.get("created_at", now)
    chunk.updated_at = kwargs.get("updated_at", now)
    chunk.page_start = kwargs.get("page_start", None)
    chunk.page_end = kwargs.get("page_end", None)
    chunk.title_path = kwargs.get("title_path", None)
    chunk.source_offset = kwargs.get("source_offset", 0)
    chunk.chunk_metadata = kwargs.get("chunk_metadata", None)
    chunk.effective_time = kwargs.get("effective_time", None)
    chunk.expiration_time = kwargs.get("expiration_time", None)
    chunk.updated_by = kwargs.get("updated_by", None)
    return chunk


class TestListChunks:

    def test_list_empty(self, client, mock_db):
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [count_result, list_result]

        response = client.get("/api/v1/document-chunks")
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 0

    def test_list_with_data(self, client, mock_db):
        chunk = _make_chunk()
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [chunk]
        mock_db.execute.side_effect = [count_result, list_result]

        response = client.get("/api/v1/document-chunks?document_id=doc-001")
        assert response.status_code == 200
        assert response.json()["data"]["total"] == 1

    def test_list_with_keyword(self, client, mock_db):
        chunk = _make_chunk(clean_text="考勤管理制度")
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [chunk]
        mock_db.execute.side_effect = [count_result, list_result]

        response = client.get("/api/v1/document-chunks?keyword=考勤")
        assert response.status_code == 200


class TestGetChunk:

    def test_get_success(self, client, mock_db):
        chunk = _make_chunk(chunk_no=5, clean_text="第五条的内容")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = chunk
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/document-chunks/chunk-001")
        assert response.status_code == 200
        assert response.json()["data"]["chunk_no"] == 5

    def test_get_not_found(self, client, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get("/api/v1/document-chunks/non-existent")
        assert response.status_code == 404
