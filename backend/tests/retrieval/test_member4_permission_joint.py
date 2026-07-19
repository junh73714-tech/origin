"""成员4 权限过滤联调用例（契约 daafd86 + 混合检索）。"""
from datetime import datetime, timedelta, timezone

from app.core.security import AccessContext
from app.providers.deterministic_embedding import DeterministicEmbeddingProvider
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.member4_bridge import (
    access_context_to_retrieval_filter,
    build_member4_style_opensearch_bool,
)
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever

DOCS = [
    {
        "chunk_id": "c1",
        "document_id": "doc_pub",
        "document_version_id": "v1",
        "knowledge_base_id": "kb_a",
        "tenant_id": "t1",
        "clean_text": "公开差旅报销制度",
        "title_path": "差旅",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 0,
    },
    {
        "chunk_id": "c2",
        "document_id": "doc_secret",
        "document_version_id": "v2",
        "knowledge_base_id": "kb_a",
        "tenant_id": "t1",
        "clean_text": "机密差旅额度",
        "title_path": "差旅",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 3,
    },
    {
        "chunk_id": "c3",
        "document_id": "doc_other_kb",
        "document_version_id": "v3",
        "knowledge_base_id": "kb_b",
        "tenant_id": "t1",
        "clean_text": "其他库差旅",
        "title_path": "差旅",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 0,
    },
    {
        "chunk_id": "c4",
        "document_id": "doc_temp",
        "document_version_id": "v4",
        "knowledge_base_id": "kb_b",
        "tenant_id": "t1",
        "clean_text": "临时授权差旅补充",
        "title_path": "差旅",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 0,
    },
]


def _svc() -> HybridRetrievalService:
    emb = DeterministicEmbeddingProvider(dimension=16, model_name="joint")
    rows = []
    for d in DOCS:
        row = dict(d)
        row["embedding"] = emb.embed_query(d["clean_text"])
        rows.append(row)
    return HybridRetrievalService(
        KeywordRetriever(client=InMemoryKeywordIndex(DOCS)),
        VectorRetriever(embedding_provider=emb, store=InMemoryVectorStore(rows)),
        permission=DefaultPermissionAdapter(),
    )


def _access(**kwargs) -> AccessContext:
    ctx = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=["employee"],
        permissions=["knowledge_base.read"],
        data_scopes={},
        knowledge_base_ids=["kb_a"],
        max_confidentiality_level=0,
        deny_document_ids=[],
        temporary_grants=[],
    )
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    ctx.scope_hash = compute_scope_hash(ctx)
    return ctx


def test_p0_empty_kb_opensearch_match_none():
    """成员4 P0：空 KB 且无临时授权 → match_none。"""
    f = access_context_to_retrieval_filter(
        _access(knowledge_base_ids=[], temporary_grants=[])
    )
    dsl = build_member4_style_opensearch_bool(f)
    assert dsl == {"bool": {"must": [{"match_none": {}}]}}


def test_p0_confidentiality_zero_still_filters():
    """成员4 P0：max==0 仍加 confidentiality_level <= 0。"""
    f = access_context_to_retrieval_filter(_access(max_confidentiality_level=0))
    dsl = build_member4_style_opensearch_bool(f)
    must = dsl["bool"]["must"]
    assert any(
        "range" in c
        and c["range"].get("confidentiality_level", {}).get("lte") == 0
        for c in must
    )


def test_p0_temp_grant_in_opensearch_dsl():
    """成员4 P0：临时授权文档进入 DSL。"""
    active = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    f = access_context_to_retrieval_filter(
        _access(
            knowledge_base_ids=[],
            temporary_grants=[
                {
                    "resource_type": "document",
                    "resource_id": "doc_temp",
                    "permission_type": "read",
                    "expiration_time": active,
                }
            ],
        )
    )
    dsl = build_member4_style_opensearch_bool(f)
    assert "match_none" not in str(dsl)
    assert "doc_temp" in str(dsl)


def test_joint_hybrid_default_deny_empty_scope():
    svc = _svc()
    result = svc.retrieve("差旅", _access(knowledge_base_ids=[]), mode="hybrid")
    assert result.fused_hits == []


def test_joint_hybrid_kb_and_confidentiality():
    svc = _svc()
    result = svc.retrieve("差旅", _access(max_confidentiality_level=0), mode="hybrid")
    ids = {h.document_id for h in result.fused_hits}
    assert "doc_pub" in ids
    assert "doc_secret" not in ids
    assert "doc_other_kb" not in ids


def test_joint_hybrid_temp_grant_cross_kb():
    svc = _svc()
    active = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    access = _access(
        knowledge_base_ids=[],
        temporary_grants=[{"document_id": "doc_temp", "expires_at": active}],
    )
    result = svc.retrieve("差旅", access, mode="hybrid")
    ids = {h.document_id for h in result.fused_hits}
    assert "doc_temp" in ids
    assert "doc_pub" not in ids
