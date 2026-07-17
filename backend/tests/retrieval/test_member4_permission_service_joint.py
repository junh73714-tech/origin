"""成员4 PermissionService → 成员6 RetrievalFilter 正式接入联调。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.security import AccessContext
from app.retrieval.member4_bridge import (
    apply_access_context_response,
    build_member4_style_opensearch_bool,
    member4_filter_dict_to_m6,
    safe_enrich_access,
)
from app.retrieval.permission_adapter import DefaultPermissionAdapter
from app.schemas.identity import AccessContextResponse, TemporaryGrantInfo
from app.services.permission_service import PermissionService


def _mock_user(*, user_id: str = "u1", tenant_id: str = "t1") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.tenant_id = tenant_id
    user.roles = []
    user.departments = []
    user.groups = []
    return user


@pytest.mark.asyncio
async def test_permission_service_empty_kb_opensearch_match_none():
    """正式 PermissionService：空 KB → match_none。"""
    mock_db = AsyncMock()
    mock_user = _mock_user()

    def _exec_result(*, scalar=None, rows=None, items=None):
        m = MagicMock()
        m.scalar_one_or_none.return_value = scalar
        m.all.return_value = rows if rows is not None else []
        m.scalars.return_value.all.return_value = items if items is not None else []
        return m

    mock_db.execute.side_effect = [
        _exec_result(scalar=mock_user),  # user
        _exec_result(rows=[]),  # allowed kb ids
        _exec_result(items=[]),  # document permissions for confidentiality
        _exec_result(items=[]),  # deny docs
        _exec_result(items=[]),  # temporary grants
    ]
    svc = PermissionService(mock_db)
    m4 = await svc.build_retrieval_filters("u1")
    m6 = member4_filter_dict_to_m6(m4.model_dump())
    dsl = build_member4_style_opensearch_bool(m6)
    assert dsl == {"bool": {"must": [{"match_none": {}}]}}
    assert m6.knowledge_base_ids == []


@pytest.mark.asyncio
async def test_permission_service_to_m6_adapter_and_hybrid_fields():
    """AccessContextResponse 富化后，DefaultPermissionAdapter 可读正式字段。"""
    exp = datetime.now(timezone.utc) + timedelta(hours=2)
    ctx = AccessContextResponse(
        tenant_id="t1",
        user_id="u1",
        role_ids=["r1"],
        department_ids=["d1"],
        group_ids=[],
        knowledge_base_ids=["kb_a"],
        project_ids=[],
        regions=[],
        max_confidentiality_level=0,
        deny_document_ids=["doc_deny"],
        temporary_grants=[
            TemporaryGrantInfo(
                resource_type="document",
                resource_id="doc_temp",
                permission_type="read",
                effective_time=datetime.now(timezone.utc) - timedelta(minutes=1),
                expiration_time=exp,
            )
        ],
        scope_hash="abc123hash",
    )
    access = AccessContext(
        user_id="u1",
        tenant_id="t1",
        roles=[],
        permissions=[],
        data_scopes={},
    )
    access = apply_access_context_response(access, ctx)
    assert access.knowledge_base_ids == ["kb_a"]
    assert access.max_confidentiality_level == 0
    assert access.deny_document_ids == ["doc_deny"]
    assert access.scope_hash == "abc123hash"

    f = DefaultPermissionAdapter().build_retrieval_filters(access)
    assert f.knowledge_base_ids == ["kb_a"]
    assert f.max_confidentiality_level == 0
    assert "doc_temp" in f.temporary_grant_document_ids
    dsl = build_member4_style_opensearch_bool(f)
    assert any(
        "range" in c and c["range"]["confidentiality_level"]["lte"] == 0
        for c in dsl["bool"]["must"]
    )


@pytest.mark.asyncio
async def test_safe_enrich_falls_back_when_user_missing(monkeypatch):
    mock_db = AsyncMock()
    access = AccessContext(
        user_id="missing",
        tenant_id="t1",
        roles=["employee"],
        permissions=["knowledge_base.read"],
        knowledge_base_ids=["kb_jwt"],
        max_confidentiality_level=3,
    )
    monkeypatch.setenv("USE_MEMBER4_PERMISSION", "1")

    async def _boom(*_a, **_k):
        raise RuntimeError("relation knowledge_base_permissions does not exist")

    monkeypatch.setattr(
        "app.retrieval.member4_bridge.enrich_access_with_permission_service",
        _boom,
    )
    out = await safe_enrich_access(mock_db, access)
    assert out.knowledge_base_ids == ["kb_jwt"]
    assert out.max_confidentiality_level == 3
