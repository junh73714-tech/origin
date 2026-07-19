"""
成员4权限契约适配器。

成员4正式 PermissionService 未就绪时，使用与 AccessContext 对齐的最小实现，
不得绕过默认拒绝与显式拒绝优先规则。系统管理员不默认拥有全部业务文档阅读权。
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Protocol

from app.core.security import AccessContext
from app.retrieval.types import RetrievalFilter, RetrievalHit, TemporaryGrantRef


class PermissionServiceProtocol(Protocol):
    """成员4权限服务协议（适配用）。"""

    def get_access_context(self, user_id: str, tenant_id: str) -> AccessContext: ...

    def build_retrieval_filters(self, access: AccessContext) -> RetrievalFilter: ...

    def can_access_chunk(self, access: AccessContext, chunk: dict[str, Any]) -> bool: ...

    def can_access_standard_qa(self, access: AccessContext, qa: dict[str, Any]) -> bool: ...

    def can_open_citation(self, access: AccessContext, citation: dict[str, Any]) -> bool: ...


def _parse_grant_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def _normalize_temporary_grant(raw: Any) -> TemporaryGrantRef | None:
    """兼容成员4 TemporaryGrantInfo 与本地 {document_id, expires_at} 字典。"""
    if isinstance(raw, TemporaryGrantRef):
        return raw
    if not isinstance(raw, dict):
        return None

    resource_type = str(raw.get("resource_type") or "document")
    resource_id = raw.get("resource_id") or raw.get("document_id")
    if not resource_id:
        return None
    # 仅文档临时授权参与检索文档 ID 过滤
    if resource_type != "document":
        return None

    return TemporaryGrantRef(
        resource_type=resource_type,
        resource_id=str(resource_id),
        permission_type=str(raw.get("permission_type") or "read"),
        effective_time=_parse_grant_time(raw.get("effective_time")),
        expiration_time=_parse_grant_time(
            raw.get("expiration_time") or raw.get("expires_at")
        ),
    )


def _active_temporary_grants(access: AccessContext) -> list[TemporaryGrantRef]:
    """返回当前仍有效的临时授权对象列表（对齐成员4 effective_temporary_grants）。"""
    now = datetime.now(timezone.utc)
    active: list[TemporaryGrantRef] = []
    for raw in getattr(access, "temporary_grants", None) or []:
        grant = _normalize_temporary_grant(raw)
        if grant is None:
            continue
        if grant.effective_time and grant.effective_time > now:
            continue
        if grant.expiration_time and grant.expiration_time <= now:
            continue
        active.append(grant)
    return active


def compute_scope_hash(access: AccessContext) -> str:
    """由规范化权限范围生成稳定摘要，不含可逆敏感数据。"""
    grants = _active_temporary_grants(access)
    payload = {
        "tenant_id": access.tenant_id,
        "user_id": access.user_id,
        "roles": sorted(access.roles or []),
        "permissions": sorted(access.permissions or []),
        "data_scopes": {
            k: sorted(v) if isinstance(v, list) else v
            for k, v in sorted((access.data_scopes or {}).items())
        },
        "role_ids": sorted(getattr(access, "role_ids", []) or []),
        "department_ids": sorted(getattr(access, "department_ids", []) or []),
        "group_ids": sorted(getattr(access, "group_ids", []) or []),
        "knowledge_base_ids": sorted(getattr(access, "knowledge_base_ids", []) or []),
        "project_ids": sorted(getattr(access, "project_ids", []) or []),
        "regions": sorted(getattr(access, "regions", []) or []),
        "max_confidentiality_level": getattr(access, "max_confidentiality_level", 0),
        "deny_document_ids": sorted(getattr(access, "deny_document_ids", []) or []),
        "temporary_grants": sorted(
            {
                f"{g.resource_type}:{g.resource_id}:{g.expiration_time.isoformat() if g.expiration_time else ''}"
                for g in grants
            }
        ),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def ensure_access_snapshot(access: AccessContext) -> AccessContext:
    """返回深拷贝不可变快照。"""
    data = copy.deepcopy(access.to_dict())
    snap = AccessContext.from_dict(data)
    if not getattr(snap, "scope_hash", None):
        snap.scope_hash = compute_scope_hash(snap)
    return snap


class DefaultPermissionAdapter:
    """
    默认权限适配：默认拒绝，显式拒绝优先。
    不因 super_admin 跳过数据权限。
    """

    def get_access_context(self, user_id: str, tenant_id: str) -> AccessContext:
        ctx = AccessContext(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=[],
            permissions=[],
            data_scopes={},
        )
        ctx.scope_hash = compute_scope_hash(ctx)
        return ctx

    def build_retrieval_filters(self, access: AccessContext) -> RetrievalFilter:
        access = ensure_access_snapshot(access)
        kb_ids = list(getattr(access, "knowledge_base_ids", None) or [])
        if not kb_ids:
            kb_ids = list((access.data_scopes or {}).get("knowledge_base", []) or [])
        deny = list(getattr(access, "deny_document_ids", None) or [])
        allow = list((access.data_scopes or {}).get("document", []) or [])
        if "*" in allow:
            allow = [x for x in allow if x != "*"]
        grants = _active_temporary_grants(access)
        return RetrievalFilter(
            tenant_id=access.tenant_id,
            user_id=access.user_id,
            knowledge_base_ids=[x for x in kb_ids if x != "*"],
            department_ids=list(getattr(access, "department_ids", []) or []),
            group_ids=list(getattr(access, "group_ids", []) or []),
            project_ids=list(getattr(access, "project_ids", []) or []),
            regions=list(getattr(access, "regions", []) or []),
            max_confidentiality_level=int(
                getattr(access, "max_confidentiality_level", 0) or 0
            ),
            deny_document_ids=deny,
            allow_document_ids=allow,
            effective_temporary_grants=grants,
            scope_hash=getattr(access, "scope_hash", "") or compute_scope_hash(access),
        )

    def can_access_chunk(self, access: AccessContext, chunk: dict[str, Any]) -> bool:
        if chunk.get("tenant_id") and chunk.get("tenant_id") != access.tenant_id:
            return False
        doc_id = chunk.get("document_id") or ""
        deny = set(getattr(access, "deny_document_ids", []) or [])
        if doc_id in deny:
            return False
        level = int(chunk.get("confidentiality_level", 0) or 0)
        max_level = int(getattr(access, "max_confidentiality_level", 0) or 0)
        if level > max_level:
            return False
        status = (
            chunk.get("document_status")
            or chunk.get("status")
            or "published"
        )
        if status in {"paused", "offlined", "offline", "expired", "draft", "pending"}:
            return False
        if chunk.get("is_current_version") is False:
            return False
        # Chunk 级失效
        chunk_status = chunk.get("chunk_status")
        if chunk_status in {"outdated", "deleted"}:
            return False

        allow = {x for x in ((access.data_scopes or {}).get("document", []) or []) if x != "*"}
        kb_allow = {
            x
            for x in (
                getattr(access, "knowledge_base_ids", None)
                or (access.data_scopes or {}).get("knowledge_base", [])
                or []
            )
            if x != "*"
        }
        temp = {g.document_id for g in _active_temporary_grants(access) if g.document_id}

        if doc_id in temp:
            return True
        # 文档白名单非空时必须命中（不再因 kb_allow 存在而绕过）
        if allow and doc_id not in allow:
            return False
        kb_id = chunk.get("knowledge_base_id") or ""
        if kb_allow and kb_id and kb_id not in kb_allow:
            return False
        # 默认拒绝：无文档白名单、无知识库范围、无临时授权
        if not allow and not kb_allow:
            return False
        return True

    def can_access_standard_qa(self, access: AccessContext, qa: dict[str, Any]) -> bool:
        if qa.get("status") != "published":
            return False
        kb_id = qa.get("knowledge_base_id") or ""
        kb_allow = {
            x
            for x in (
                getattr(access, "knowledge_base_ids", None)
                or (access.data_scopes or {}).get("knowledge_base", [])
                or []
            )
            if x != "*"
        }
        if kb_allow and kb_id not in kb_allow:
            return False
        source_docs = qa.get("source_document_ids") or []
        if not source_docs:
            # 无来源文档时仅按知识库范围；仍默认拒绝空范围
            return bool(kb_allow) or bool(_active_temporary_grants(access))
        for doc_id in source_docs:
            if not self.can_access_chunk(
                access,
                {
                    "tenant_id": access.tenant_id,
                    "document_id": doc_id,
                    "knowledge_base_id": kb_id,
                    "status": "published",
                    "is_current_version": True,
                    "confidentiality_level": qa.get("confidentiality_level", 0),
                },
            ):
                return False
        return True

    def can_open_citation(self, access: AccessContext, citation: dict[str, Any]) -> bool:
        return self.can_access_chunk(
            access,
            {
                "tenant_id": citation.get("tenant_id") or access.tenant_id,
                "document_id": citation.get("document_id"),
                "knowledge_base_id": citation.get("knowledge_base_id"),
                "status": citation.get("source_status") or citation.get("status") or "published",
                "is_current_version": citation.get("is_current_version", True),
                "confidentiality_level": citation.get("confidentiality_level", 0),
            },
        )


def filter_hits_before_body(
    hits: list[RetrievalHit],
    access: AccessContext,
    adapter: DefaultPermissionAdapter | None = None,
) -> list[RetrievalHit]:
    """在正文读取前按权限过滤候选（防御性二次过滤）。"""
    adapter = adapter or DefaultPermissionAdapter()
    kept: list[RetrievalHit] = []
    for hit in hits:
        if adapter.can_access_chunk(
            access,
            {
                "tenant_id": access.tenant_id,
                "document_id": hit.document_id,
                "knowledge_base_id": hit.knowledge_base_id,
                "status": hit.status,
                "is_current_version": hit.is_current_version,
                "confidentiality_level": hit.confidentiality_level,
            },
        ):
            kept.append(hit)
    return kept
