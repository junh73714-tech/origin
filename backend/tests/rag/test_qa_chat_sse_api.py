"""/qa/chat SSE 端到端自测（成员6 第4步）。

覆盖认证依赖注入带权限 AccessContext，注入内存索引（已发布文档），
验证 SSE 事件序列、citation、权限过滤（空 KB 默认拒绝）。
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import qa as qa_module
from app.core.dependencies import get_required_access_context
from app.core.security import AccessContext
from app.providers.deterministic_embedding import DeterministicEmbeddingProvider
from app.rag.graph import QAGraph
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.permission_adapter import compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever


def _build_app() -> FastAPI:
    """最小 app：仅挂载 qa 路由，避免 minio/opensearch 等无关依赖。"""
    mini = FastAPI()
    mini.include_router(qa_module.router, prefix="/api/v1/qa")
    return mini


DOCS = [
    {
        "chunk_id": "c1",
        "document_id": "doc_pub",
        "document_version_id": "v1",
        "knowledge_base_id": "kb_a",
        "tenant_id": "t1",
        "clean_text": "公司差旅报销标准为每日不超过500元，需在7个工作日内提交。",
        "title_path": "差旅制度/报销",
        "document_name": "差旅制度.pdf",
        "page_start": 1,
        "page_end": 1,
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 0,
    }
]


def _install_graph(monkeypatch, kb_ids: list[str]):
    emb = DeterministicEmbeddingProvider(dimension=16, model_name="sse-selftest")
    rows = [{**d, "embedding": emb.embed_query(d["clean_text"])} for d in DOCS]
    retrieval = HybridRetrievalService(
        KeywordRetriever(client=InMemoryKeywordIndex(DOCS)),
        VectorRetriever(embedding_provider=emb, store=InMemoryVectorStore(rows)),
    )
    graph = QAGraph(retrieval=retrieval)
    monkeypatch.setattr(qa_module, "_graph", graph)


def _access(kb_ids: list[str]) -> AccessContext:
    ctx = AccessContext(
        user_id="selftest_u1",
        tenant_id="t1",
        roles=["employee"],
        permissions=["knowledge_base.read"],
        knowledge_base_ids=kb_ids,
        max_confidentiality_level=3,
        deny_document_ids=[],
        temporary_grants=[],
    )
    ctx.scope_hash = compute_scope_hash(ctx)
    return ctx


def _client(monkeypatch, kb_ids: list[str]) -> tuple[TestClient, FastAPI]:
    _install_graph(monkeypatch, kb_ids)
    mini = _build_app()
    mini.dependency_overrides[get_required_access_context] = lambda: _access(kb_ids)
    return TestClient(mini), mini


def _read_sse(resp) -> str:
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    return resp.text


def test_chat_sse_sequence_and_citation(monkeypatch):
    client, mini = _client(monkeypatch, kb_ids=["kb_a"])
    try:
        resp = client.post(
            "/api/v1/qa/chat",
            json={"content": "差旅报销标准是多少？"},
            headers={"X-Request-ID": "req_selftest_1"},
        )
        body = _read_sse(resp)
    finally:
        mini.dependency_overrides.clear()

    assert "event: message_start" in body
    assert "event: answer_delta" in body
    assert "event: done" in body
    # 命中已发布文档应产生引用
    assert "event: citation" in body
    assert "doc_pub" in body or "差旅" in body


def test_chat_sse_empty_scope_no_citation(monkeypatch):
    """空 KB 范围：默认拒绝，不应召回文档，也不应有 citation。"""
    client, mini = _client(monkeypatch, kb_ids=[])
    try:
        resp = client.post(
            "/api/v1/qa/chat",
            json={"content": "差旅报销标准是多少？"},
        )
        body = _read_sse(resp)
    finally:
        mini.dependency_overrides.clear()

    assert "event: message_start" in body
    assert "event: done" in body
    assert "event: citation" not in body
