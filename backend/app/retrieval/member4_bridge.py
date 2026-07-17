"""
成员4 PermissionService 正式接入桥接。

推荐路径：
  ctx = await PermissionService(db).get_access_context(user_id=...)
  filters = PermissionService(db)._build_retrieval_filter_from_context(ctx)
  m6_filters = member4_filter_dict_to_m6(filters.model_dump())

AccessContext 富化后，DefaultPermissionAdapter.build_retrieval_filters 亦可直接使用。
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import AccessContext
from app.retrieval.permission_adapter import DefaultPermissionAdapter
from app.retrieval.types import RetrievalFilter, TemporaryGrantRef

logger = get_logger(__name__)


def use_member4_permission() -> bool:
    """是否启用正式 PermissionService 富化（默认开启，失败时回退 JWT 上下文）。"""
    flag = os.getenv("USE_MEMBER4_PERMISSION", "1").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def access_context_to_retrieval_filter(access: AccessContext) -> RetrievalFilter:
    """成员6 侧统一入口：从 AccessContext 构建 RetrievalFilter。"""
    return DefaultPermissionAdapter().build_retrieval_filters(access)


def build_member4_style_opensearch_bool(filters: RetrievalFilter) -> dict[str, Any]:
    """
    按成员4 daafd86 的 build_opensearch_filter 语义生成 bool DSL。

    P0 对齐：
    - 空 KB 且无临时授权文档 → match_none（默认拒绝）
    - 始终 confidentiality_level <= max（含 max==0）
    - 临时授权 document resource_id 进入 should/OR
    """
    temp_doc_ids = [
        g.resource_id
        for g in filters.effective_temporary_grants
        if g.resource_type == "document" and g.resource_id
    ]
    if not temp_doc_ids:
        temp_doc_ids = list(filters.temporary_grant_document_ids)

    if not filters.knowledge_base_ids and not temp_doc_ids:
        return {"bool": {"must": [{"match_none": {}}]}}

    must: list[dict[str, Any]] = [{"term": {"tenant_id": filters.tenant_id}}]
    must_not: list[dict[str, Any]] = []

    if filters.knowledge_base_ids:
        must.append({"terms": {"knowledge_base_id": list(filters.knowledge_base_ids)}})

    must.append(
        {
            "range": {
                "confidentiality_level": {"lte": filters.max_confidentiality_level}
            }
        }
    )

    if filters.deny_document_ids:
        must_not.append({"terms": {"document_id": list(filters.deny_document_ids)}})

    if temp_doc_ids:
        should: list[dict[str, Any]] = [{"terms": {"document_id": temp_doc_ids}}]
        if filters.knowledge_base_ids:
            should.append(
                {"terms": {"knowledge_base_id": list(filters.knowledge_base_ids)}}
            )
        must.append({"bool": {"should": should, "minimum_should_match": 1}})

    body: dict[str, Any] = {"bool": {"must": must}}
    if must_not:
        body["bool"]["must_not"] = must_not
    return body


def member4_filter_dict_to_m6(data: dict[str, Any]) -> RetrievalFilter:
    """将成员4 RetrievalFilter.model_dump() 转为成员6 RetrievalFilter。"""
    grants_raw = data.get("effective_temporary_grants") or []
    grants: list[TemporaryGrantRef] = []
    for g in grants_raw:
        if isinstance(g, TemporaryGrantRef):
            grants.append(g)
            continue
        if not isinstance(g, dict):
            continue
        grants.append(
            TemporaryGrantRef(
                resource_type=str(g.get("resource_type") or "document"),
                resource_id=str(g.get("resource_id") or g.get("document_id") or ""),
                permission_type=str(g.get("permission_type") or "read"),
                effective_time=g.get("effective_time"),
                expiration_time=g.get("expiration_time") or g.get("expires_at"),
            )
        )
    return RetrievalFilter(
        tenant_id=str(data["tenant_id"]),
        user_id=str(data.get("user_id") or ""),
        knowledge_base_ids=list(data.get("knowledge_base_ids") or []),
        department_ids=list(data.get("department_ids") or []),
        group_ids=list(data.get("group_ids") or []),
        project_ids=list(data.get("project_ids") or []),
        regions=list(data.get("regions") or []),
        max_confidentiality_level=int(data.get("max_confidentiality_level") or 0),
        deny_document_ids=list(data.get("deny_document_ids") or []),
        allow_document_ids=list(data.get("allow_document_ids") or []),
        effective_temporary_grants=grants,
        require_published=bool(data.get("require_published", True)),
        require_current_version=bool(data.get("require_current_version", True)),
        exclude_paused=bool(data.get("exclude_paused", True)),
        exclude_offlined=bool(data.get("exclude_offlined", True)),
        exclude_expired=bool(data.get("exclude_expired", True)),
        scope_hash=str(data.get("scope_hash") or ""),
    )


def apply_access_context_response(access: AccessContext, ctx: Any) -> AccessContext:
    """把成员4 AccessContextResponse 写回成员6 AccessContext。"""
    access.tenant_id = getattr(ctx, "tenant_id", None) or access.tenant_id
    access.user_id = getattr(ctx, "user_id", None) or access.user_id
    access.role_ids = list(getattr(ctx, "role_ids", None) or [])
    access.department_ids = list(getattr(ctx, "department_ids", None) or [])
    access.group_ids = list(getattr(ctx, "group_ids", None) or [])
    access.knowledge_base_ids = list(getattr(ctx, "knowledge_base_ids", None) or [])
    access.project_ids = list(getattr(ctx, "project_ids", None) or [])
    access.regions = list(getattr(ctx, "regions", None) or [])
    access.max_confidentiality_level = int(
        getattr(ctx, "max_confidentiality_level", 0) or 0
    )
    access.deny_document_ids = list(getattr(ctx, "deny_document_ids", None) or [])
    grants = []
    for g in getattr(ctx, "temporary_grants", None) or []:
        if hasattr(g, "model_dump"):
            grants.append(g.model_dump())
        elif isinstance(g, dict):
            grants.append(g)
    access.temporary_grants = grants
    access.scope_hash = str(getattr(ctx, "scope_hash", "") or "")
    access.data_scopes = {
        **(access.data_scopes or {}),
        "knowledge_base": list(access.knowledge_base_ids),
        "document": list(getattr(ctx, "allow_document_ids", None) or []),
        "deny_document_ids": list(access.deny_document_ids),
        "max_confidentiality_level": access.max_confidentiality_level,
        "temporary_grants": list(access.temporary_grants),
        "scope_hash": access.scope_hash,
    }
    return access


async def enrich_access_with_permission_service(
    db: AsyncSession,
    access: AccessContext,
) -> AccessContext:
    """
    使用正式 PermissionService.get_access_context 富化 AccessContext。
    表缺失或用户不存在时抛出异常，由调用方决定是否回退。
    """
    from app.services.permission_service import PermissionService

    svc = PermissionService(db)
    ctx = await svc.get_access_context(
        tenant_id=access.tenant_id or None,
        user_id=access.user_id,
    )
    return apply_access_context_response(access, ctx)


async def build_m6_filters_from_permission_service(
    db: AsyncSession,
    user_id: str,
) -> RetrievalFilter:
    """正式路径：PermissionService → 成员6 RetrievalFilter。"""
    from app.services.permission_service import PermissionService

    svc = PermissionService(db)
    m4_filters = await svc.build_retrieval_filters(user_id)
    data = m4_filters.model_dump() if hasattr(m4_filters, "model_dump") else dict(m4_filters)
    return member4_filter_dict_to_m6(data)


async def safe_enrich_access(
    db: AsyncSession | None,
    access: AccessContext,
) -> AccessContext:
    """富化失败时保留 JWT/调用方上下文，不阻断主链路。"""
    if db is None or not use_member4_permission() or not access.user_id:
        return access
    if access.user_id == "anonymous":
        return access
    try:
        return await enrich_access_with_permission_service(db, access)
    except Exception as exc:  # noqa: BLE001 - 联调期显式降级
        logger.warning(
            "permission_service_enrich_failed",
            user_id=access.user_id,
            error=str(exc),
        )
        return access
