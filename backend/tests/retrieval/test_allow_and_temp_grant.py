"""文档白名单与临时授权测试。"""
from datetime import datetime, timedelta, timezone

from app.core.security import AccessContext
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash
from app.retrieval.types import RetrievalFilter, TemporaryGrantRef


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


def test_temp_grant_member4_object_shape():
    """成员4 TemporaryGrantInfo 形状（resource_id）可被适配并进入过滤。"""
    adapter = DefaultPermissionAdapter()
    active = datetime.now(timezone.utc) + timedelta(hours=2)
    access = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=[],
        permissions=[],
        data_scopes={},
        knowledge_base_ids=[],
        temporary_grants=[
            {
                "resource_type": "document",
                "resource_id": "doc_m4",
                "permission_type": "read",
                "effective_time": datetime.now(timezone.utc) - timedelta(minutes=1),
                "expiration_time": active,
            }
        ],
    )
    assert adapter.can_access_chunk(
        access,
        {
            "tenant_id": "t1",
            "document_id": "doc_m4",
            "status": "published",
            "is_current_version": True,
        },
    )
    filters = adapter.build_retrieval_filters(access)
    assert filters.user_id == "u1"
    assert len(filters.effective_temporary_grants) == 1
    assert filters.temporary_grant_document_ids == ["doc_m4"]


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
    f = RetrievalFilter(tenant_id="t1", user_id="u1")
    clauses = f.to_opensearch_filter()
    assert any(
        "terms" in c and c["terms"].get("document_id") == ["__no_access__"] for c in clauses
    )


def test_retrieval_filter_temp_grants_as_objects():
    grant = TemporaryGrantRef(
        resource_type="document",
        resource_id="doc_1",
        permission_type="read",
        expiration_time=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    f = RetrievalFilter(
        tenant_id="t1",
        user_id="u1",
        effective_temporary_grants=[grant],
    )
    assert f.temporary_grant_document_ids == ["doc_1"]
    where = f.to_pgvector_where()
    assert where["user_id"] == "u1"
    assert where["temporary_grant_document_ids"] == ["doc_1"]
    assert len(where["effective_temporary_grants"]) == 1
