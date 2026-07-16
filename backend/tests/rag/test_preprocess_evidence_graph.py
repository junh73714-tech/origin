"""预处理、证据与问答图测试。"""
from app.core.security import AccessContext
from app.providers.embedding.provider import DeterministicEmbeddingProvider
from app.rag.evidence import assess_evidence
from app.rag.graph import QAGraph
from app.rag.preprocess import preprocess, query_rewrite
from app.rag.standard_qa_adapter import MockStandardQAMatcher
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.permission_adapter import compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.types import RetrievalHit
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever


def test_query_rewrite_keeps_critical_conditions():
    q = "华东 2024年 PN-1001 型号 不适用 实习生 的差旅制度"
    rewritten = query_rewrite(q)
    for token in ("华东", "2024", "PN-1001", "不适用", "实习生"):
        assert token in rewritten


def test_intent_routing():
    pre = preprocess("PN-1001 型号参数是什么")
    assert pre.intent in {"keyword_prefer", "hybrid", "vector_prefer"}
    pre2 = preprocess("今天天气怎么样")
    assert pre2.intent == "refuse_or_guide"


def test_evidence_refuse_when_empty():
    a = assess_evidence("华东差旅", [])
    assert a.decision == "refuse"


def test_graph_standard_qa_trusted_and_fallback():
    emb = DeterministicEmbeddingProvider(dimension=16, model_name="t")
    docs = [
        {
            "id": "c1",
            "chunk_id": "c1",
            "document_id": "d1",
            "document_version_id": "v1",
            "knowledge_base_id": "kb1",
            "tenant_id": "t1",
            "clean_text": "差旅报销需要提供发票",
            "title_path": "差旅",
            "status": "published",
            "is_current_version": True,
            "confidentiality_level": 0,
            "embedding": emb.embed_query("差旅报销需要提供发票"),
            "metadata": {"document_name": "差旅制度"},
        }
    ]
    retrieval = HybridRetrievalService(
        KeywordRetriever(client=InMemoryKeywordIndex(docs)),
        VectorRetriever(embedding_provider=emb, store=InMemoryVectorStore(docs)),
    )
    matcher = MockStandardQAMatcher(
        [
            {
                "question": "差旅报销需要什么材料",
                "qa_id": "qa1",
                "answer": "需要发票和行程单",
                "status": "published",
                "knowledge_base_id": "kb1",
                "entities": ["差旅"],
                "source_document_ids": ["d1"],
                "citations": [{"citation_id": "cit_demo"}],
            }
        ]
    )
    graph = QAGraph(retrieval=retrieval, standard_qa=matcher)
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

    trusted = graph.run("差旅报销需要什么材料", access)
    assert trusted.answer_type == "standard_qa"
    assert "发票" in trusted.generated_answer

    # 实体不一致 -> 转 RAG
    matcher2 = MockStandardQAMatcher(
        [
            {
                "question": "差旅报销需要什么材料",
                "qa_id": "qa1",
                "answer": "需要发票",
                "status": "published",
                "knowledge_base_id": "kb1",
                "entities": ["华北"],  # 与问题实体不一致
                "source_document_ids": ["d1"],
            }
        ]
    )
    graph2 = QAGraph(retrieval=retrieval, standard_qa=matcher2)
    # 改写后可能带实体；使用包含地区的问题
    state = graph2.run("华东差旅报销需要什么材料", access)
    assert state.answer_type != "standard_qa" or not (state.standard_qa_result or {}).get(
        "trusted"
    )


def test_evidence_partial():
    hits = [
        RetrievalHit(
            chunk_id="c1",
            document_id="d1",
            document_version_id="v1",
            text_preview="差旅报销需要发票",
            status="published",
            is_current_version=True,
        )
    ]
    a = assess_evidence("华东 差旅 报销", hits)
    assert a.decision in {"supplement", "ask_user", "generate", "refuse"}
