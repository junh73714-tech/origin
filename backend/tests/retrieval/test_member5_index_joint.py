"""成员5 Embedding/索引字段联调用例（契约层，内存索引）。"""
from __future__ import annotations

import os

from app.core.security import AccessContext
from app.providers.deterministic_embedding import (
    DeterministicEmbeddingProvider,
    get_embedding_provider,
)
from app.retrieval.index_status import is_dual_index_ready
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.types import RetrievalFilter
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever


DOCS = [
    {
        "chunk_id": "c_pub",
        "document_id": "doc_pub",
        "document_version_id": "ver_pub",
        "knowledge_base_id": "kb1",
        "tenant_id": "t1",
        "clean_text": "已发布差旅报销规则",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 0,
        "permission_metadata": {
            "tenant_id": "t1",
            "knowledge_base_id": "kb1",
            "max_confidentiality_level": 0,
        },
    },
    {
        "chunk_id": "c_old",
        "document_id": "doc_pub",
        "document_version_id": "ver_old",
        "knowledge_base_id": "kb1",
        "tenant_id": "t1",
        "clean_text": "旧版本差旅规则不应召回",
        "status": "active",
        "document_status": "published",
        "is_current_version": False,
        "confidentiality_level": 0,
        "permission_metadata": {"tenant_id": "t1", "knowledge_base_id": "kb1"},
    },
    {
        "chunk_id": "c_off",
        "document_id": "doc_off",
        "document_version_id": "ver_off",
        "knowledge_base_id": "kb1",
        "tenant_id": "t1",
        "clean_text": "已下线差旅规则",
        "status": "active",
        "document_status": "offlined",
        "is_current_version": True,
        "confidentiality_level": 0,
        "permission_metadata": {"tenant_id": "t1"},
    },
    {
        "chunk_id": "c_draft",
        "document_id": "doc_draft",
        "document_version_id": "ver_draft",
        "knowledge_base_id": "kb1",
        "tenant_id": "t1",
        "clean_text": "草稿差旅规则",
        "status": "active",
        "document_status": "draft",
        "is_current_version": True,
        "confidentiality_level": 0,
        "permission_metadata": {},
    },
]


def _access() -> AccessContext:
    ctx = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=["employee"],
        permissions=["knowledge_base.read"],
        knowledge_base_ids=["kb1"],
        max_confidentiality_level=5,
        deny_document_ids=[],
        temporary_grants=[],
    )
    ctx.scope_hash = compute_scope_hash(ctx)
    return ctx


def _svc() -> HybridRetrievalService:
    emb = DeterministicEmbeddingProvider(dimension=16, model_name="m5-joint")
    rows = [{**d, "embedding": emb.embed_query(d["clean_text"])} for d in DOCS]
    return HybridRetrievalService(
        KeywordRetriever(client=InMemoryKeywordIndex(DOCS)),
        VectorRetriever(embedding_provider=emb, store=InMemoryVectorStore(rows)),
        permission=DefaultPermissionAdapter(),
    )


def test_joint_only_published_current_version():
    result = _svc().retrieve("差旅", _access(), mode="hybrid")
    ids = {h.chunk_id for h in result.fused_hits}
    assert "c_pub" in ids
    assert "c_old" not in ids
    assert "c_off" not in ids
    assert "c_draft" not in ids


def test_opensearch_filter_uses_member5_fields():
    f = RetrievalFilter(
        tenant_id="t1",
        user_id="u1",
        knowledge_base_ids=["kb1"],
        max_confidentiality_level=5,
        require_published=True,
        require_current_version=True,
    )
    clauses = f.to_opensearch_filter()
    assert {"term": {"status": "active"}} in clauses
    assert {"term": {"document_status": "published"}} in clauses
    assert {"term": {"is_current_version": True}} in clauses


def test_permission_metadata_present_on_published_chunk():
    pub = next(d for d in DOCS if d["chunk_id"] == "c_pub")
    assert pub["permission_metadata"]
    assert pub["permission_metadata"].get("tenant_id") == "t1"
    assert pub["permission_metadata"].get("knowledge_base_id") == "kb1"


def test_dual_index_ready_gate():
    assert is_dual_index_ready(
        {
            "document_version_id": "v1",
            "opensearch": "completed",
            "pgvector": "completed",
            "opensearch_count": 3,
            "pgvector_count": 3,
        }
    )
    assert not is_dual_index_ready(
        {"opensearch": "completed", "pgvector": "pending"}
    )
    assert not is_dual_index_ready(
        {"opensearch": "failed", "pgvector": "completed"}
    )


def test_default_embedding_provider_is_deterministic(monkeypatch):
    monkeypatch.delenv("USE_MEMBER5_EMBEDDING", raising=False)
    provider = get_embedding_provider()
    assert isinstance(provider, DeterministicEmbeddingProvider)
    vec = provider.embed_query("联调")
    assert len(vec) == provider.dimension
    assert abs(sum(x * x for x in vec) - 1.0) < 1e-5


def test_member5_embedding_switch_uses_adapter(monkeypatch):
    """开关打开时走 Member5EmbeddingAdapter（不发起真实 API）。"""
    from app.providers import deterministic_embedding as de

    class _Fake:
        model = "fake-emb"
        model_version = "vtest"
        dimension = 8

        def embed_query(self, text: str) -> list[float]:
            return [0.125] * 8

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[0.125] * 8 for _ in texts]

    def _fake_init(self, provider=None) -> None:
        self._inner = _Fake()
        self.model_name = "fake-emb"
        self.model_version = "vtest"
        self.dimension = 8

    monkeypatch.setenv("USE_MEMBER5_EMBEDDING", "1")
    monkeypatch.setattr(de.Member5EmbeddingAdapter, "__init__", _fake_init)
    provider = get_embedding_provider()
    assert provider.model_name == "fake-emb"
    assert len(provider.embed_query("x")) == 8
    assert os.getenv("USE_MEMBER5_EMBEDDING") == "1"
