"""
成员6 ↔ 成员4 权限过滤联调冒烟脚本。

用法（在 backend 目录）：
  python -m pytest tests/retrieval/test_member4_permission_joint.py -v
  或：
  python ../scripts/m6_permission_filter_joint.py

说明：
- 当前分支尚未合入 PermissionService（成员4 PR#11），本脚本用契约对齐的适配层 + 内存索引验证过滤语义。
- 正式 DB 联调需：成员4 合入 develop、.env 可用、seed 用户/权限数据后，再替换为 PermissionService.get_access_context。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(ROOT))

from app.core.security import AccessContext  # noqa: E402
from app.providers.deterministic_embedding import DeterministicEmbeddingProvider  # noqa: E402
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever  # noqa: E402
from app.retrieval.member4_bridge import (  # noqa: E402
    access_context_to_retrieval_filter,
    build_member4_style_opensearch_bool,
)
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash  # noqa: E402
from app.retrieval.service import HybridRetrievalService  # noqa: E402
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever  # noqa: E402


def _access(**kwargs) -> AccessContext:
    ctx = AccessContext(
        user_id="joint_u1",
        tenant_id="t1",
        roles=["employee"],
        permissions=["knowledge_base.read"],
        knowledge_base_ids=["kb_a"],
        max_confidentiality_level=0,
        deny_document_ids=[],
        temporary_grants=[],
    )
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    ctx.scope_hash = compute_scope_hash(ctx)
    return ctx


def main() -> int:
    docs = [
        {
            "chunk_id": "c1",
            "document_id": "doc_pub",
            "document_version_id": "v1",
            "knowledge_base_id": "kb_a",
            "tenant_id": "t1",
            "clean_text": "公开制度",
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
            "clean_text": "机密制度",
            "status": "active",
            "document_status": "published",
            "is_current_version": True,
            "confidentiality_level": 5,
        },
    ]
    emb = DeterministicEmbeddingProvider(dimension=8, model_name="smoke")
    rows = [{**d, "embedding": emb.embed_query(d["clean_text"])} for d in docs]
    svc = HybridRetrievalService(
        KeywordRetriever(InMemoryKeywordIndex(docs)),
        VectorRetriever(emb, InMemoryVectorStore(rows)),
        DefaultPermissionAdapter(),
    )

    cases: list[tuple[str, bool]] = []

    # P0-1 空范围
    f0 = access_context_to_retrieval_filter(_access(knowledge_base_ids=[]))
    dsl0 = build_member4_style_opensearch_bool(f0)
    cases.append(("空KB默认拒绝(match_none)", "match_none" in str(dsl0)))

    # P0-2 密级0
    f1 = access_context_to_retrieval_filter(_access(max_confidentiality_level=0))
    dsl1 = build_member4_style_opensearch_bool(f1)
    cases.append(("密级0仍过滤", '"lte": 0' in str(dsl1).replace(" ", "") or "lte': 0" in str(dsl1)))

    r = svc.retrieve("制度", _access(max_confidentiality_level=0), mode="hybrid")
    ids = {h.document_id for h in r.fused_hits}
    cases.append(("混合检索密级过滤", ids == {"doc_pub"}))

    # 临时授权
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    f2 = access_context_to_retrieval_filter(
        _access(
            knowledge_base_ids=[],
            temporary_grants=[{"document_id": "doc_secret", "expires_at": exp}],
        )
    )
    dsl2 = build_member4_style_opensearch_bool(f2)
    cases.append(("临时授权进入DSL", "doc_secret" in str(dsl2) and "match_none" not in str(dsl2)))

    print("=== member6-member4 permission filter joint smoke ===")
    failed = 0
    for name, ok in cases:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{status}] {name}")
    print(f"total: {len(cases) - failed}/{len(cases)} passed")
    if failed:
        print("FAIL: contract layer. Need PermissionService on develop for DB joint test.")
        return 1
    print("PASS: contract joint OK. Next: merge member4 PR + .env + seed, then wire PermissionService.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
