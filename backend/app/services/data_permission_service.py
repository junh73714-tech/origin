"""
成员4：数据权限和临时授权服务
实现知识库权限、文档权限、临时授权的管理
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.identity import DocumentPermission, KnowledgeBasePermission, TemporaryGrant
from app.schemas.common import PaginatedData
from app.schemas.identity import (
    DocumentPermissionCreate,
    DocumentPermissionResponse,
    KnowledgeBasePermissionCreate,
    KnowledgeBasePermissionResponse,
    TemporaryGrantCreate,
    TemporaryGrantResponse,
    TemporaryGrantUpdate,
)

logger = get_logger(__name__)


class DataPermissionService:
    """数据权限服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_knowledge_base_permission(
        self,
        create_data: KnowledgeBasePermissionCreate,
        created_by: str = "system",
    ) -> KnowledgeBasePermissionResponse:
        """创建知识库权限"""
        existing = await self.db.execute(
            select(KnowledgeBasePermission)
            .filter(
                and_(
                    KnowledgeBasePermission.knowledge_base_id == create_data.knowledge_base_id,
                    KnowledgeBasePermission.user_id == create_data.user_id,
                    KnowledgeBasePermission.role_id == create_data.role_id,
                    KnowledgeBasePermission.department_id == create_data.department_id,
                    KnowledgeBasePermission.group_id == create_data.group_id,
                    KnowledgeBasePermission.permission_type == create_data.permission_type,
                    KnowledgeBasePermission.deleted_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError(resource_type="知识库权限", identifier=str(create_data))

        permission = KnowledgeBasePermission(
            id=f"kbp_{uuid.uuid4().hex[:16]}",
            tenant_id="default",
            knowledge_base_id=create_data.knowledge_base_id,
            user_id=create_data.user_id,
            role_id=create_data.role_id,
            department_id=create_data.department_id,
            group_id=create_data.group_id,
            permission_type=create_data.permission_type,
            is_deny=create_data.is_deny,
            effective_time=create_data.effective_time,
            expiration_time=create_data.expiration_time,
            created_by=created_by,
        )
        self.db.add(permission)
        await self.db.flush()

        logger.info("knowledge_base_permission_created", permission_id=permission.id, kb_id=create_data.knowledge_base_id)

        return KnowledgeBasePermissionResponse.model_validate(permission)

    async def list_knowledge_base_permissions(
        self,
        knowledge_base_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedData[KnowledgeBasePermissionResponse]:
        """获取知识库权限列表"""
        query = select(KnowledgeBasePermission).filter(KnowledgeBasePermission.deleted_at.is_(None))

        if knowledge_base_id:
            query = query.filter(KnowledgeBasePermission.knowledge_base_id == knowledge_base_id)

        count_query = select(func.count(KnowledgeBasePermission.id)).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(KnowledgeBasePermission.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        permissions = result.scalars().all()

        items = [KnowledgeBasePermissionResponse.model_validate(p) for p in permissions]

        return PaginatedData.create(items, total, page, page_size)

    async def delete_knowledge_base_permission(self, permission_id: str, deleted_by: str = "system") -> None:
        """删除知识库权限"""
        permission = await self.db.execute(
            select(KnowledgeBasePermission)
            .filter(
                and_(
                    KnowledgeBasePermission.id == permission_id,
                    KnowledgeBasePermission.deleted_at.is_(None),
                )
            )
        )
        permission = permission.scalar_one_or_none()
        if not permission:
            raise ResourceNotFoundError(resource_type="知识库权限", resource_id=permission_id)

        permission.deleted_at = func.now()
        permission.deleted_by = deleted_by
        await self.db.flush()

        logger.info("knowledge_base_permission_deleted", permission_id=permission_id)

    async def create_document_permission(
        self,
        create_data: DocumentPermissionCreate,
        created_by: str = "system",
    ) -> DocumentPermissionResponse:
        """创建文档权限"""
        existing = await self.db.execute(
            select(DocumentPermission)
            .filter(
                and_(
                    DocumentPermission.document_id == create_data.document_id,
                    DocumentPermission.user_id == create_data.user_id,
                    DocumentPermission.role_id == create_data.role_id,
                    DocumentPermission.department_id == create_data.department_id,
                    DocumentPermission.group_id == create_data.group_id,
                    DocumentPermission.permission_type == create_data.permission_type,
                    DocumentPermission.deleted_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError(resource_type="文档权限", identifier=str(create_data))

        permission = DocumentPermission(
            id=f"dp_{uuid.uuid4().hex[:16]}",
            tenant_id="default",
            document_id=create_data.document_id,
            user_id=create_data.user_id,
            role_id=create_data.role_id,
            department_id=create_data.department_id,
            group_id=create_data.group_id,
            permission_type=create_data.permission_type,
            is_deny=create_data.is_deny,
            confidentiality_level=create_data.confidentiality_level,
            effective_time=create_data.effective_time,
            expiration_time=create_data.expiration_time,
            created_by=created_by,
        )
        self.db.add(permission)
        await self.db.flush()

        logger.info("document_permission_created", permission_id=permission.id, doc_id=create_data.document_id)

        return DocumentPermissionResponse.model_validate(permission)

    async def list_document_permissions(
        self,
        document_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedData[DocumentPermissionResponse]:
        """获取文档权限列表"""
        query = select(DocumentPermission).filter(DocumentPermission.deleted_at.is_(None))

        if document_id:
            query = query.filter(DocumentPermission.document_id == document_id)

        count_query = select(func.count(DocumentPermission.id)).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(DocumentPermission.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        permissions = result.scalars().all()

        items = [DocumentPermissionResponse.model_validate(p) for p in permissions]

        return PaginatedData.create(items, total, page, page_size)

    async def delete_document_permission(self, permission_id: str, deleted_by: str = "system") -> None:
        """删除文档权限"""
        permission = await self.db.execute(
            select(DocumentPermission)
            .filter(
                and_(
                    DocumentPermission.id == permission_id,
                    DocumentPermission.deleted_at.is_(None),
                )
            )
        )
        permission = permission.scalar_one_or_none()
        if not permission:
            raise ResourceNotFoundError(resource_type="文档权限", resource_id=permission_id)

        permission.deleted_at = func.now()
        permission.deleted_by = deleted_by
        await self.db.flush()

        logger.info("document_permission_deleted", permission_id=permission_id)

    async def create_temporary_grant(
        self,
        create_data: TemporaryGrantCreate,
        created_by: str = "system",
    ) -> TemporaryGrantResponse:
        """创建临时授权"""
        now = datetime.now(timezone.utc)
        if create_data.effective_time >= create_data.expiration_time:
            raise ValidationError(message="生效时间必须早于失效时间")

        if create_data.expiration_time <= now:
            raise ValidationError(message="失效时间必须在未来")

        grant = TemporaryGrant(
            id=f"tg_{uuid.uuid4().hex[:16]}",
            tenant_id="default",
            user_id=create_data.user_id,
            resource_type=create_data.resource_type,
            resource_id=create_data.resource_id,
            permission_type=create_data.permission_type,
            reason=create_data.reason,
            effective_time=create_data.effective_time,
            expiration_time=create_data.expiration_time,
            status="active",
            created_by=created_by,
        )
        self.db.add(grant)
        await self.db.flush()

        logger.info("temporary_grant_created", grant_id=grant.id, user_id=create_data.user_id, resource_id=create_data.resource_id)

        return TemporaryGrantResponse.model_validate(grant)

    async def list_temporary_grants(
        self,
        user_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedData[TemporaryGrantResponse]:
        """获取临时授权列表"""
        query = select(TemporaryGrant).filter(TemporaryGrant.deleted_at.is_(None))

        if user_id:
            query = query.filter(TemporaryGrant.user_id == user_id)

        if status:
            query = query.filter(TemporaryGrant.status == status)

        count_query = select(func.count(TemporaryGrant.id)).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(TemporaryGrant.expiration_time)
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        grants = result.scalars().all()

        items = [TemporaryGrantResponse.model_validate(g) for g in grants]

        return PaginatedData.create(items, total, page, page_size)

    async def get_temporary_grant(self, grant_id: str) -> TemporaryGrantResponse | None:
        """获取临时授权详情"""
        result = await self.db.execute(
            select(TemporaryGrant)
            .filter(
                and_(
                    TemporaryGrant.id == grant_id,
                    TemporaryGrant.deleted_at.is_(None),
                )
            )
        )
        grant = result.scalar_one_or_none()
        if not grant:
            return None
        return TemporaryGrantResponse.model_validate(grant)

    async def update_temporary_grant(
        self,
        grant_id: str,
        update_data: TemporaryGrantUpdate,
        updated_by: str = "system",
    ) -> TemporaryGrantResponse:
        """更新临时授权"""
        result = await self.db.execute(
            select(TemporaryGrant)
            .filter(
                and_(
                    TemporaryGrant.id == grant_id,
                    TemporaryGrant.deleted_at.is_(None),
                )
            )
        )
        grant = result.scalar_one_or_none()
        if not grant:
            raise ResourceNotFoundError(resource_type="临时授权", resource_id=grant_id)

        if update_data.status is not None:
            grant.status = update_data.status

        if update_data.reason is not None:
            grant.reason = update_data.reason

        grant.updated_by = updated_by
        await self.db.flush()

        logger.info("temporary_grant_updated", grant_id=grant_id)

        return TemporaryGrantResponse.model_validate(grant)

    async def delete_temporary_grant(self, grant_id: str, deleted_by: str = "system") -> None:
        """删除临时授权"""
        result = await self.db.execute(
            select(TemporaryGrant)
            .filter(
                and_(
                    TemporaryGrant.id == grant_id,
                    TemporaryGrant.deleted_at.is_(None),
                )
            )
        )
        grant = result.scalar_one_or_none()
        if not grant:
            raise ResourceNotFoundError(resource_type="临时授权", resource_id=grant_id)

        grant.deleted_at = func.now()
        grant.deleted_by = deleted_by
        await self.db.flush()

        logger.info("temporary_grant_deleted", grant_id=grant_id)

    async def check_expired_grants(self) -> list[TemporaryGrant]:
        """检查过期的临时授权"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(TemporaryGrant)
            .filter(
                and_(
                    TemporaryGrant.status == "active",
                    TemporaryGrant.expiration_time <= now,
                    TemporaryGrant.deleted_at.is_(None),
                )
            )
        )
        expired_grants = result.scalars().all()

        for grant in expired_grants:
            grant.status = "expired"
            logger.info("temporary_grant_expired", grant_id=grant.id, user_id=grant.user_id)

        await self.db.flush()

        return expired_grants