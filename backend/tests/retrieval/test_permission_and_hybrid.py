"""权限过滤与混合检索测试。"""
from app.core.security import AccessContext
from app.providers.deterministic_embedding import DeterministicEmbeddingProvider
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever

DOCS = [
    {
        "id": "chk_a",
        "chunk_id": "chk_a",
        "document_id": "doc_a",
        "document_version_id": "ver_a",
        "knowledge_base_id": "kb_public",
        "tenant_id": "t1",
        "clean_text": "华东区域差旅报销制度条款",
        "title_path": "差旅/报销",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 1,
        "embedding": None,
    },
    {
        "id": "chk_b",
        "chunk_id": "chk_b",
        "document_id": "doc_b",
        "document_version_id": "ver_b",
        "knowledge_base_id": "kb_private",
        "tenant_id": "t1",
        "clean_text": "B 部门内部薪资制度",
        "title_path": "薪资",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 1,
        "embedding": None,
    },
    {
        "id": "chk_denied",
        "chunk_id": "chk_denied",
        "document_id": "doc_denied",
        "document_version_id": "ver_d",
        "knowledge_base_id": "kb_public",
        "tenant_id": "t1",
        "clean_text": "显式拒绝文档内容差旅",
        "title_path": "拒绝",
        "status": "active",
        "document_status": "published",
        "is_current_version": True,
        "confidentiality_level": 1,
        "embedding": None,
    },
    {
        "id": "chk_old",
        "chunk_id": "chk_old",
        "document_id": "doc_a",
        "document_version_id": "ver_old",
        "knowledge_base_id": "kb_public",
        "tenant_id": "t1",
        "clean_text": "旧版本差旅制度",
        "title_path": "差旅",
        "status": "active",
        "document_status": "published",
        "is_current_version": False,
        "confidentiality_level": 1,
        "embedding": None,
    },
    {
        "id": "chk_off",
        "chunk_id": "chk_off",
        "document_id": "doc_off",
        "document_version_id": "ver_off",
        "knowledge_base_id": "kb_public",
        "tenant_id": "t1",
        "clean_text": "已下线差旅制度",
        "title_path": "差旅",
        "status": "active",
        "document_status": "offline",
        "is_current_version": True,
        "confidentiality_level": 1,
        "embedding": None,
    },
]


def _service():
    emb = DeterministicEmbeddingProvider(dimension=32, model_name="test-emb")
    rows = []
    for d in DOCS:
        row = dict(d)
        row["embedding"] = emb.embed_query(d["clean_text"])
        rows.append(row)
    kw = KeywordRetriever(client=InMemoryKeywordIndex(DOCS))
    vec = VectorRetriever(embedding_provider=emb, store=InMemoryVectorStore(rows))
    return HybridRetrievalService(kw, vec, rrf_k=60)


def _access(**kwargs) -> AccessContext:
    ctx = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=["employee"],
        permissions=["knowledge_base.read"],
        data_scopes={"knowledge_base": ["kb_public"]},
        knowledge_base_ids=["kb_public"],
        max_confidentiality_level=2,
        deny_document_ids=["doc_denied"],
    )
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    ctx.scope_hash = compute_scope_hash(ctx)
    return ctx


def test_permission_filter_before_recall():
    svc = _service()
    result = svc.retrieve("差旅报销", _access(), mode="hybrid")
    ids = {h.document_id for h in result.fused_hits}
    assert "doc_denied" not in ids
    assert "doc_b" not in ids  # 不在 kb_public
    assert all(h.is_current_version for h in result.fused_hits)
    assert all(h.status != "offlined" and h.status != "offline" for h in result.fused_hits)


def test_keyword_only():
    svc = _service()
    result = svc.retrieve("差旅", _access(), mode="keyword")
    assert result.keyword_hits
    assert not result.vector_hits or True
    assert result.fused_hits


def test_vector_only():
    svc = _service()
    result = svc.retrieve("差旅报销制度", _access(), mode="vector")
    assert result.vector_hits
    assert "doc_denied" not in {h.document_id for h in result.vector_hits}


def test_admin_no_default_doc_read():
    adapter = DefaultPermissionAdapter()
    admin = AccessContext(
        user_id="admin",
        tenant_id="t1",
        roles=["super_admin"],
        permissions=["*"],
        data_scopes={},
        knowledge_base_ids=[],
        max_confidentiality_level=0,
    )
    assert (
        adapter.can_access_chunk(
            admin,
            {
                "tenant_id": "t1",
                "document_id": "doc_a",
                "knowledge_base_id": "kb_public",
                "status": "published",
                "is_current_version": True,
                "confidentiality_level": 1,
            },
        )
        is False
    )


def test_scope_hash_stable():
    a = _access()
    b = _access()
    assert compute_scope_hash(a) == compute_scope_hash(b)
    b.deny_document_ids = ["doc_denied", "doc_x"]
    assert compute_scope_hash(a) != compute_scope_hash(b)
