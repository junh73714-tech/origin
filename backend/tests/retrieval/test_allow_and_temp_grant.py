"""文档白名单与临时授权测试。"""
from datetime import datetime, timedelta, timezone

from app.core.security import AccessContext
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash
from app.retrieval.types import RetrievalFilter


def test_document_allow_list_not_bypassed_by_kb():
    adapter = DefaultPermissionAdapter()
    access = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=[],
        permissions=[],
        data_scopes={"document": ["doc_a"], "knowledge_base": ["kb1"]},
        knowledge_base_ids=["kb1"],
        max_confidentiality_level=5,
    )
    assert adapter.can_access_chunk(
        access,
        {
            "tenant_id": "t1",
            "document_id": "doc_a",
            "knowledge_base_id": "kb1",
            "status": "published",
            "is_current_version": True,
        },
    )
    assert not adapter.can_access_chunk(
        access,
        {
            "tenant_id": "t1",
            "document_id": "doc_other",
            "knowledge_base_id": "kb1",
            "status": "published",
            "is_current_version": True,
        },
    )


def test_temp_grant_expiry():
    adapter = DefaultPermissionAdapter()
    expired = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    active = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    access = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=[],
        permissions=[],
        data_scopes={},
        knowledge_base_ids=[],
        temporary_grants=[{"document_id": "doc_x", "expires_at": expired}],
    )
    assert not adapter.can_access_chunk(
        access,
        {
            "tenant_id": "t1",
            "document_id": "doc_x",
            "status": "published",
            "is_current_version": True,
        },
    )
    access.temporary_grants = [{"document_id": "doc_x", "expires_at": active}]
    assert adapter.can_access_chunk(
        access,
        {
            "tenant_id": "t1",
            "document_id": "doc_x",
            "status": "published",
            "is_current_version": True,
        },
    )


def test_scope_hash_includes_temp_grants():
    a = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=[],
        permissions=[],
        temporary_grants=[],
    )
    b = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=[],
        permissions=[],
        temporary_grants=[
            {
                "document_id": "doc_x",
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            }
        ],
    )
    assert compute_scope_hash(a) != compute_scope_hash(b)


def test_opensearch_filter_default_deny_empty_scope():
    f = RetrievalFilter(tenant_id="t1")
    clauses = f.to_opensearch_filter()
    assert any(
        "terms" in c and c["terms"].get("document_id") == ["__no_access__"] for c in clauses
    )
