"""
成员4：PermissionService
全项目唯一的权限服务，提供权限查询、校验、检索过滤和缓存失效能力
实现权限计算规则：默认拒绝、显式拒绝优先、功能权限与数据权限分离、多角色合并等
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError
from app.core.logging import get_logger
from app.core.security import AccessContext
from app.models.auth import Permission, Role
from app.models.identity import (
    DocumentPermission,
    KnowledgeBasePermission,
    TemporaryGrant,
    Department,
    UserGroup,
)
from app.models.user import User
from app.schemas.identity import (
    AccessContextResponse,
    OpenSearchFilterDSL,
    PostgreSQLFilter,
    RetrievalFilter,
    TemporaryGrantInfo,
)

logger = get_logger(__name__)


class PermissionService:
    """权限服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_access_context(self, user_id: str) -> AccessContextResponse:
        """获取用户访问上下文快照"""
        user = await self._get_user_with_relations(user_id)
        if not user:
            raise AuthorizationError(message="用户不存在")

        role_ids = [role.id for role in user.roles]
        department_ids = [dept.id for dept in user.departments]
        group_ids = [group.id for group in user.groups]
        roles = [role.code for role in user.roles]
        permissions = [perm.code for role in user.roles for perm in role.permissions]

        knowledge_base_ids = await self._get_allowed_knowledge_base_ids(user)
        max_confidentiality_level = await self._get_max_confidentiality_level(user)
        deny_document_ids = await self._get_deny_document_ids(user)
        temporary_grants = await self._get_active_temporary_grants(user_id)

        data_scopes = {
            "knowledge_base": knowledge_base_ids,
            "document": [],
        }

        temp_grant_entries = sorted(
            {
                f"{g.resource_id}:{g.expiration_time.isoformat()}"
                for g in temporary_grants
            }
        )

        scope_data = {
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "roles": sorted(roles),
            "permissions": sorted(permissions),
            "data_scopes": {
                k: sorted(v) if isinstance(v, list) else v
                for k, v in sorted(data_scopes.items())
            },
            "role_ids": sorted(role_ids),
            "department_ids": sorted(department_ids),
            "group_ids": sorted(group_ids),
            "knowledge_base_ids": sorted(knowledge_base_ids),
            "project_ids": [],
            "regions": [],
            "max_confidentiality_level": max_confidentiality_level,
            "deny_document_ids": sorted(deny_document_ids),
            "temporary_grants": temp_grant_entries,
        }

        scope_hash = self._compute_scope_hash(scope_data)

        return AccessContextResponse(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role_ids=role_ids,
            department_ids=department_ids,
            group_ids=group_ids,
            knowledge_base_ids=knowledge_base_ids,
            project_ids=[],
            regions=[],
            max_confidentiality_level=max_confidentiality_level,
            deny_document_ids=deny_document_ids,
            temporary_grants=[TemporaryGrantInfo.model_validate(g) for g in temporary_grants],
            scope_hash=scope_hash,
        )

    async def get_user_access_scope(self, user_id: str) -> dict[str, Any]:
        """获取用户访问范围摘要"""
        context = await self.get_access_context(user_id)
        return {
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "role_ids": context.role_ids,
            "department_ids": context.department_ids,
            "group_ids": context.group_ids,
            "scope_hash": context.scope_hash,
        }

    async def build_retrieval_filters(self, user_id: str) -> RetrievalFilter:
        """构建检索过滤条件"""
        context = await self.get_access_context(user_id)

        return RetrievalFilter(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            knowledge_base_ids=context.knowledge_base_ids,
            department_ids=context.department_ids,
            group_ids=context.group_ids,
            max_confidentiality_level=context.max_confidentiality_level,
            deny_document_ids=context.deny_document_ids,
            effective_temporary_grants=[
                TemporaryGrantInfo.model_validate(g)
                for g in context.temporary_grants
            ],
            scope_hash=context.scope_hash,
        )

    async def build_opensearch_filter(self, user_id: str) -> OpenSearchFilterDSL:
        """构建 OpenSearch 过滤 DSL"""
        filters = await self.build_retrieval_filters(user_id)

        must_clauses = []
        must_not_clauses = []

        must_clauses.append({"term": {"tenant_id": filters.tenant_id}})

        if filters.knowledge_base_ids:
            must_clauses.append(
                {"terms": {"knowledge_base_id": filters.knowledge_base_ids}}
            )

        if filters.max_confidentiality_level > 0:
            must_clauses.append(
                {"range": {"confidentiality_level": {"lte": filters.max_confidentiality_level}}}
            )

        if filters.deny_document_ids:
            must_not_clauses.append(
                {"terms": {"document_id": filters.deny_document_ids}}
            )

        return OpenSearchFilterDSL(
            bool={
                "must": must_clauses,
                "must_not": must_not_clauses,
            }
        )

    async def build_postgresql_filter(self, user_id: str) -> PostgreSQLFilter:
        """构建 PostgreSQL 过滤条件"""
        filters = await self.build_retrieval_filters(user_id)

        conditions = []
        params = {"tenant_id": filters.tenant_id}

        conditions.append("tenant_id = :tenant_id")

        if filters.knowledge_base_ids:
            conditions.append(f"knowledge_base_id IN ({','.join([':kb_' + str(i) for i in range(len(filters.knowledge_base_ids))])})")
            for i, kb_id in enumerate(filters.knowledge_base_ids):
                params[f"kb_{i}"] = kb_id

        if filters.max_confidentiality_level > 0:
            conditions.append("confidentiality_level <= :max_confidentiality_level")
            params["max_confidentiality_level"] = filters.max_confidentiality_level

        if filters.deny_document_ids:
            conditions.append(f"document_id NOT IN ({','.join([':deny_' + str(i) for i in range(len(filters.deny_document_ids))])})")
            for i, doc_id in enumerate(filters.deny_document_ids):
                params[f"deny_{i}"] = doc_id

        where_clause = " AND ".join(conditions) if conditions else ""

        return PostgreSQLFilter(
            where_clause=where_clause,
            params=params,
        )

    async def can_execute_action(self, user_id: str, action: str) -> bool:
        """检查用户是否可以执行指定操作"""
        user = await self._get_user_with_relations(user_id)
        if not user:
            return False

        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.code)

        if "*" in permissions:
            return True

        return action in permissions

    async def can_access_knowledge_base(self, user_id: str, knowledge_base_id: str) -> bool:
        """检查用户是否可以访问知识库"""
        user = await self._get_user_with_relations(user_id)
        if not user:
            return False

        kb_permissions = await self._get_knowledge_base_permissions(knowledge_base_id)

        deny_rules = [p for p in kb_permissions if p.is_deny]
        allow_rules = [p for p in kb_permissions if not p.is_deny]

        for rule in deny_rules:
            if await self._matches_user(user, rule):
                return False

        for rule in allow_rules:
            if await self._matches_user(user, rule):
                return True

        return False

    async def can_access_document(self, user_id: str, document_id: str) -> bool:
        """检查用户是否可以访问文档"""
        user = await self._get_user_with_relations(user_id)
        if not user:
            return False

        doc_permissions = await self._get_document_permissions(document_id)

        deny_rules = [p for p in doc_permissions if p.is_deny]
        allow_rules = [p for p in doc_permissions if not p.is_deny]

        for rule in deny_rules:
            if await self._matches_user(user, rule):
                return False

        for rule in allow_rules:
            if await self._matches_user(user, rule):
                return True

        temporary_grants = await self._get_active_temporary_grants(user_id)
        for grant in temporary_grants:
            if grant.resource_type == "document" and grant.resource_id == document_id:
                return True

        return False

    async def can_access_chunk(self, user_id: str, chunk_id: str) -> bool:
        """检查用户是否可以访问Chunk"""
        doc_id = await self._get_document_id_by_chunk(chunk_id)
        if not doc_id:
            return False

        return await self.can_access_document(user_id, doc_id)

    async def can_access_standard_qa(self, user_id: str, qa_id: str) -> bool:
        """检查用户是否可以访问标准问答"""
        document_ids = await self._get_document_ids_by_qa(qa_id)
        if not document_ids:
            return False

        for doc_id in document_ids:
            if not await self.can_access_document(user_id, doc_id):
                return False

        return True

    async def can_open_citation(self, user_id: str, citation_data: dict[str, Any]) -> bool:
        """检查用户是否可以打开引用"""
        document_id = citation_data.get("document_id")
        chunk_id = citation_data.get("chunk_id")

        if document_id:
            return await self.can_access_document(user_id, document_id)

        if chunk_id:
            return await self.can_access_chunk(user_id, chunk_id)

        return False

    async def invalidate_user_permission_cache(self, user_id: str) -> None:
        """失效用户权限缓存"""
        from app.services.cache_service import invalidate_permission_cache
        await invalidate_permission_cache(user_id)
        logger.info("permission_cache_invalidated", user_id=user_id)

    async def _get_user_with_relations(self, user_id: str) -> User | None:
        """获取用户及其所有关系"""
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.departments),
                selectinload(User.groups),
            )
            .filter(
                and_(
                    User.id == user_id,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_allowed_knowledge_base_ids(self, user: User) -> list[str]:
        """获取用户允许访问的知识库ID列表"""
        result = await self.db.execute(
            select(KnowledgeBasePermission.knowledge_base_id)
            .filter(
                and_(
                    KnowledgeBasePermission.is_deny.is_(False),
                    KnowledgeBasePermission.deleted_at.is_(None),
                )
            )
        )
        all_allowed_kb_ids = [row[0] for row in result.all()]

        user_role_ids = {role.id for role in user.roles}
        user_dept_ids = {dept.id for dept in user.departments}
        user_group_ids = {group.id for group in user.groups}

        allowed_ids = []
        for kb_id in all_allowed_kb_ids:
            kb_perms = await self._get_knowledge_base_permissions(kb_id)
            for perm in kb_perms:
                if not perm.is_deny:
                    if perm.user_id == user.id:
                        allowed_ids.append(kb_id)
                        break
                    if perm.role_id and perm.role_id in user_role_ids:
                        allowed_ids.append(kb_id)
                        break
                    if perm.department_id and perm.department_id in user_dept_ids:
                        allowed_ids.append(kb_id)
                        break
                    if perm.group_id and perm.group_id in user_group_ids:
                        allowed_ids.append(kb_id)
                        break

        return list(set(allowed_ids))

    async def _get_max_confidentiality_level(self, user: User) -> int:
        """获取用户可访问的最大文档密级"""
        max_level = 0

        user_role_ids = {role.id for role in user.roles}
        user_dept_ids = {dept.id for dept in user.departments}
        user_group_ids = {group.id for group in user.groups}

        result = await self.db.execute(
            select(DocumentPermission)
            .filter(
                and_(
                    DocumentPermission.is_deny.is_(False),
                    DocumentPermission.deleted_at.is_(None),
                )
            )
        )
        perms = result.scalars().all()

        for perm in perms:
            matches = False
            if perm.user_id == user.id:
                matches = True
            elif perm.role_id and perm.role_id in user_role_ids:
                matches = True
            elif perm.department_id and perm.department_id in user_dept_ids:
                matches = True
            elif perm.group_id and perm.group_id in user_group_ids:
                matches = True

            if matches and perm.confidentiality_level > max_level:
                max_level = perm.confidentiality_level

        return max_level

    async def _get_deny_document_ids(self, user: User) -> list[str]:
        """获取用户被显式拒绝的文档ID列表"""
        user_role_ids = {role.id for role in user.roles}
        user_dept_ids = {dept.id for dept in user.departments}
        user_group_ids = {group.id for group in user.groups}

        result = await self.db.execute(
            select(DocumentPermission)
            .filter(
                and_(
                    DocumentPermission.is_deny.is_(True),
                    DocumentPermission.deleted_at.is_(None),
                )
            )
        )
        deny_perms = result.scalars().all()

        deny_doc_ids = []
        for perm in deny_perms:
            if perm.user_id == user.id:
                deny_doc_ids.append(perm.document_id)
            elif perm.role_id and perm.role_id in user_role_ids:
                deny_doc_ids.append(perm.document_id)
            elif perm.department_id and perm.department_id in user_dept_ids:
                deny_doc_ids.append(perm.document_id)
            elif perm.group_id and perm.group_id in user_group_ids:
                deny_doc_ids.append(perm.document_id)

        return list(set(deny_doc_ids))

    async def _get_active_temporary_grants(self, user_id: str) -> list[TemporaryGrant]:
        """获取用户有效的临时授权"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(TemporaryGrant)
            .filter(
                and_(
                    TemporaryGrant.user_id == user_id,
                    TemporaryGrant.status == "active",
                    TemporaryGrant.effective_time <= now,
                    TemporaryGrant.expiration_time > now,
                    TemporaryGrant.deleted_at.is_(None),
                )
            )
        )
        return result.scalars().all()

    async def _get_knowledge_base_permissions(self, knowledge_base_id: str) -> list[KnowledgeBasePermission]:
        """获取知识库权限"""
        result = await self.db.execute(
            select(KnowledgeBasePermission)
            .filter(
                and_(
                    KnowledgeBasePermission.knowledge_base_id == knowledge_base_id,
                    KnowledgeBasePermission.deleted_at.is_(None),
                )
            )
        )
        return result.scalars().all()

    async def _get_document_permissions(self, document_id: str) -> list[DocumentPermission]:
        """获取文档权限"""
        result = await self.db.execute(
            select(DocumentPermission)
            .filter(
                and_(
                    DocumentPermission.document_id == document_id,
                    DocumentPermission.deleted_at.is_(None),
                )
            )
        )
        return result.scalars().all()

    async def _matches_user(self, user: User, permission: KnowledgeBasePermission | DocumentPermission) -> bool:
        """检查权限规则是否匹配用户"""
        user_role_ids = {role.id for role in user.roles}
        user_dept_ids = {dept.id for dept in user.departments}
        user_group_ids = {group.id for group in user.groups}

        if permission.user_id and permission.user_id == user.id:
            return True
        if permission.role_id and permission.role_id in user_role_ids:
            return True
        if permission.department_id and permission.department_id in user_dept_ids:
            return True
        if permission.group_id and permission.group_id in user_group_ids:
            return True

        return False

    async def _get_document_id_by_chunk(self, chunk_id: str) -> str | None:
        """根据Chunk ID获取文档ID"""
        from app.models.document import DocumentChunk
        result = await self.db.execute(
            select(DocumentChunk.document_id)
            .filter(DocumentChunk.id == chunk_id)
        )
        row = result.first()
        return row[0] if row else None

    async def _get_document_ids_by_qa(self, qa_id: str) -> list[str]:
        """根据标准问答ID获取文档ID列表"""
        from app.models.qa import StandardQA, QAReference
        result = await self.db.execute(
            select(QAReference.document_id)
            .join(StandardQA, StandardQA.id == QAReference.qa_id)
            .filter(StandardQA.id == qa_id)
        )
        return [row[0] for row in result.all()]

    def _compute_scope_hash(self, scope_data: dict[str, Any]) -> str:
        """计算权限范围哈希值"""
        serialized = json.dumps(scope_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()