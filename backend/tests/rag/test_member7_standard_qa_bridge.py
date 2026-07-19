"""
成员7标准问答桥接联调：三场景。

1) 可信命中直出
2) 实体不一致 -> trusted=False -> 转正式 RAG
3) 未命中 -> 走 RAG
"""
from __future__ import annotations

from app.core.security import AccessContext
from app.providers.deterministic_embedding import DeterministicEmbeddingProvider
from app.rag.graph import QAGraph
from app.rag.standard_qa_adapter import (
    Member7StandardQABridge,
    StandardQAMatchResult,
    map_member7_response,
)
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.permission_adapter import compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever


class FakeMember7MatchingService:
    """契约替身：返回成员7 {matched, results:[...]} 结构。"""

    def __init__(self, response: dict):
        self._response = response
        self.last_kwargs: dict | None = None

    async def match(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


def _access() -> AccessContext:
    access = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=["user"],
        permissions=["knowledge_base.read"],
        knowledge_base_ids=["kb1"],
        data_scopes={"knowledge_base": ["kb1"], "document": ["d1"]},
        max_confidentiality_level=5,
    )
    access.scope_hash = compute_scope_hash(access)
    return access


def _retrieval_with_doc() -> HybridRetrievalService:
    emb = DeterministicEmbeddingProvider(dimension=8)
    docs = [
        {
            "chunk_id": "c1",
            "document_id": "d1",
            "document_version_id": "v1",
            "knowledge_base_id": "kb1",
            "tenant_id": "t1",
            "clean_text": "差旅报销需要发票和行程单",
            "status": "active",
            "document_status": "published",
            "is_current_version": True,
            "confidentiality_level": 0,
            "permission_metadata": {"tenant_id": "t1", "knowledge_base_id": "kb1"},
            "embedding": emb.embed_query("差旅报销需要发票和行程单"),
            "metadata": {"document_name": "差旅制度"},
        }
    ]
    return HybridRetrievalService(
        KeywordRetriever(client=InMemoryKeywordIndex(docs)),
        VectorRetriever(embedding_provider=emb, store=InMemoryVectorStore(docs)),
    )


def test_map_member7_response_takes_first_result_and_trusted():
    mapped = map_member7_response(
        {
            "matched": True,
            "results": [
                {
                    "matched": True,
                    "trusted": True,
                    "qa_id": "qa1",
                    "answer": "需要发票",
                    "final_score": 0.9,
                    "entity_consistency": 1.0,
                    "scope_consistency": 1.0,
                    "source_document_ids": ["d1"],
                    "knowledge_base_id": "kb1",
                    "status": "published",
                    "citations": [{"document_id": "d1", "document_version": 1}],
                }
            ],
        }
    )
    assert isinstance(mapped, StandardQAMatchResult)
    assert mapped.trusted is True
    assert mapped.qa_id == "qa1"
    assert mapped.citations[0]["document_version_id"] == 1


def test_scene_trusted_direct_answer():
    """场景1：可信命中直出。"""
    svc = FakeMember7MatchingService(
        {
            "matched": True,
            "results": [
                {
                    "matched": True,
                    "trusted": True,
                    "qa_id": "qa_trust",
                    "answer": "标准答案：需要发票和行程单",
                    "final_score": 0.91,
                    "entity_consistency": 1.0,
                    "scope_consistency": 1.0,
                    "status": "published",
                    "reason": "匹配成功",
                    "source_document_ids": ["d1"],
                    "knowledge_base_id": "kb1",
                    "citations": [{"citation_id": "cit1", "document_id": "d1"}],
                }
            ],
        }
    )
    bridge = Member7StandardQABridge(svc)
    graph = QAGraph(retrieval=_retrieval_with_doc(), standard_qa=bridge)
    state = graph.run("差旅报销需要什么材料", _access())
    assert state.answer_type == "standard_qa"
    assert "发票" in state.generated_answer
    assert (state.standard_qa_result or {}).get("trusted") is True
    assert svc.last_kwargs is not None
    assert "query" in svc.last_kwargs


def test_scene_entity_mismatch_fallback_rag():
    """场景2：实体不一致不可信，转入正式 RAG。"""
    svc = FakeMember7MatchingService(
        {
            "matched": True,
            "results": [
                {
                    "matched": True,
                    "trusted": False,
                    "qa_id": "qa_entity",
                    "answer": "不应直出的答案",
                    "final_score": 0.4,
                    "entity_consistency": 0.2,
                    "scope_consistency": 1.0,
                    "status": "published",
                    "reason": "实体不一致，转入正式 RAG",
                    "source_document_ids": ["d1"],
                    "knowledge_base_id": "kb1",
                }
            ],
        }
    )
    bridge = Member7StandardQABridge(svc)
    graph = QAGraph(retrieval=_retrieval_with_doc(), standard_qa=bridge)
    state = graph.run("差旅报销需要什么材料", _access())
    assert (state.standard_qa_result or {}).get("trusted") is False
    assert state.answer_type != "standard_qa"


def test_scene_no_match_fallback_rag():
    """场景3：未命中走 RAG。"""
    svc = FakeMember7MatchingService({"matched": False, "results": []})
    bridge = Member7StandardQABridge(svc)
    graph = QAGraph(retrieval=_retrieval_with_doc(), standard_qa=bridge)
    state = graph.run("差旅报销需要什么材料", _access())
    assert (state.standard_qa_result or {}).get("matched") is False
    assert state.answer_type != "standard_qa"
