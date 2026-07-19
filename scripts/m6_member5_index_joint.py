"""
成员6 <-> 成员5 Embedding/索引联调冒烟（契约层）。

用法:
  cd backend
  python -m pytest tests/retrieval/test_member5_index_joint.py -v
  python ../scripts/m6_member5_index_joint.py

正式环境联调还需:
  1) 成员1: .env + OpenSearch 9200
  2) alembic upgrade head
  3) USE_MEMBER5_EMBEDDING=1
  4) 成员5: 至少 1 篇 published 文档写入 rag_chunks + chunk_vectors
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(ROOT))

from app.core.security import AccessContext  # noqa: E402
from app.providers.deterministic_embedding import DeterministicEmbeddingProvider  # noqa: E402
from app.retrieval.index_status import is_dual_index_ready  # noqa: E402
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever  # noqa: E402
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash  # noqa: E402
from app.retrieval.service import HybridRetrievalService  # noqa: E402
from app.retrieval.types import RetrievalFilter  # noqa: E402
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever  # noqa: E402


def main() -> int:
    docs = [
        {
            "chunk_id": "c_pub",
            "document_id": "doc_pub",
            "document_version_id": "v1",
            "knowledge_base_id": "kb1",
            "tenant_id": "t1",
            "clean_text": "published policy",
            "status": "active",
            "document_status": "published",
            "is_current_version": True,
            "confidentiality_level": 0,
            "permission_metadata": {"tenant_id": "t1", "knowledge_base_id": "kb1"},
        },
        {
            "chunk_id": "c_off",
            "document_id": "doc_off",
            "document_version_id": "v2",
            "knowledge_base_id": "kb1",
            "tenant_id": "t1",
            "clean_text": "offline policy",
            "status": "active",
            "document_status": "offlined",
            "is_current_version": True,
            "confidentiality_level": 0,
            "permission_metadata": {"tenant_id": "t1"},
        },
    ]
    emb = DeterministicEmbeddingProvider(dimension=8, model_name="m5-smoke")
    rows = [{**d, "embedding": emb.embed_query(d["clean_text"])} for d in docs]
    svc = HybridRetrievalService(
        KeywordRetriever(InMemoryKeywordIndex(docs)),
        VectorRetriever(emb, InMemoryVectorStore(rows)),
        DefaultPermissionAdapter(),
    )
    access = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=[],
        permissions=[],
        knowledge_base_ids=["kb1"],
        max_confidentiality_level=5,
    )
    access.scope_hash = compute_scope_hash(access)

    cases: list[tuple[str, bool]] = []

    clauses = RetrievalFilter(
        tenant_id="t1",
        knowledge_base_ids=["kb1"],
        require_published=True,
        require_current_version=True,
    ).to_opensearch_filter()
    cases.append(
        (
            "OS filter uses document_status+is_current_version",
            {"term": {"document_status": "published"}} in clauses
            and {"term": {"is_current_version": True}} in clauses,
        )
    )

    result = svc.retrieve("policy", access, mode="hybrid")
    ids = {h.chunk_id for h in result.fused_hits}
    cases.append(("hybrid only published", ids == {"c_pub"}))

    cases.append(
        (
            "permission_metadata non-empty on published",
            bool(docs[0]["permission_metadata"]),
        )
    )
    cases.append(
        (
            "dual index ready gate",
            is_dual_index_ready({"opensearch": "completed", "pgvector": "completed"})
            and not is_dual_index_ready(
                {"opensearch": "completed", "pgvector": "pending"}
            ),
        )
    )

    print("=== member6-member5 index/embedding joint smoke ===")
    failed = 0
    for name, ok in cases:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed += 1
    print(f"total: {len(cases) - failed}/{len(cases)} passed")
    if failed:
        return 1
    print(
        "PASS: contract joint OK. Next: .env + OpenSearch + member5 seed + "
        "USE_MEMBER5_EMBEDDING=1 for live joint."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
