"""
成员4 权限过滤联调桥接。

在 PermissionService 尚未合入 develop 前，用与成员4（daafd86）一致的规则
构建 OpenSearch/pgvector 过滤语义，供成员6 检索联调。

正式路径（PermissionService 合入后）：
  filters = await permission_service.build_retrieval_filters(user_id)
  或 sync: permission_service.build_retrieval_filters_sync(access)  # 注意 sync 版字段不完整，优先用 async+AccessContextResponse
"""
from __future__ import annotations

from typing import Any

from app.core.security import AccessContext
from app.retrieval.permission_adapter import DefaultPermissionAdapter
from app.retrieval.types import RetrievalFilter, TemporaryGrantRef


def access_context_to_retrieval_filter(access: AccessContext) -> RetrievalFilter:
    """成员6 侧统一入口：从 AccessContext 构建 RetrievalFilter（契约对齐成员4）。"""
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
    # 亦兼容属性提取
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
