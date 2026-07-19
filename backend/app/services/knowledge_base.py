"""
知识库业务服务

提供知识库的创建、查询、更新、启用/停用、统计和权限管理功能。

成员5主责：知识库完整生命周期管理
"""
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BusinessStateError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from app.models.document import (
    KnowledgeBase,
    Document,
    DocumentChunk,
    IndexTask,
    DocumentProcessLog,
)
from app.models.identity import KnowledgeBasePermission
from app.schemas.document import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBasePermissionCreate,
    KnowledgeBaseStatsResponse,
)
from app.schemas.common import PaginationParams


class KnowledgeBaseService:
    """知识库业务服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # 知识库CRUD
    # -------------------------------------------------------------------------

    async def create_knowledge_base(
        self,
        tenant_id: str,
        user_id: str,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:
        """创建知识库"""
        # 检查同名知识库
        existing = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.tenant_id == tenant_id,
                KnowledgeBase.name == data.name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateResourceError(
                resource_type="知识库",
                identifier=data.name,
            )

        kb = KnowledgeBase(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            icon=data.icon,
            is_public=data.is_public,
            status="active",
            business_domain=data.business_domain,
            settings=data.settings,
            created_by=user_id,
        )
        self.db.add(kb)
        await self.db.flush()
        return kb

    async def get_knowledge_base(self, kb_id: str, tenant_id: str) -> KnowledgeBase:
        """获取知识库详情"""
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise ResourceNotFoundError(resource_type="知识库", resource_id=kb_id)
        return kb

    async def list_knowledge_bases(
        self,
        tenant_id: str,
        pagination: PaginationParams,
        keyword: str | None = None,
        status: str | None = None,
    ) -> tuple[list[KnowledgeBase], int]:
        """分页查询知识库列表"""
        # 构建基础查询
        query = select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant_id,
        )

        # 关键词搜索
        if keyword:
            query = query.where(
                KnowledgeBase.name.ilike(f"%{keyword}%")
            )

        # 状态筛选
        if status:
            query = query.where(KnowledgeBase.status == status)

        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询
        query = query.offset(pagination.offset).limit(pagination.limit)
        query = query.order_by(KnowledgeBase.created_at.desc())
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update_knowledge_base(
        self,
        kb_id: str,
        tenant_id: str,
        data: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        """更新知识库"""
        kb = await self.get_knowledge_base(kb_id, tenant_id)

        # 只更新提供的字段
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(kb, field, value)

        await self.db.flush()
        return kb

    async def enable_knowledge_base(self, kb_id: str, tenant_id: str) -> KnowledgeBase:
        """启用知识库"""
        kb = await self.get_knowledge_base(kb_id, tenant_id)

        if kb.status == "active":
            raise BusinessStateError(
                message="知识库已处于启用状态",
                current_state=kb.status,
                expected_state="disabled",
            )

        kb.status = "active"
        await self.db.flush()
        return kb

    async def disable_knowledge_base(self, kb_id: str, tenant_id: str) -> KnowledgeBase:
        """停用知识库

        停用后不允许新检索，但不删除历史数据。
        """
        kb = await self.get_knowledge_base(kb_id, tenant_id)

        if kb.status == "disabled":
            raise BusinessStateError(
                message="知识库已处于停用状态",
                current_state=kb.status,
                expected_state="active",
            )

        kb.status = "disabled"
        await self.db.flush()
        return kb

    # -------------------------------------------------------------------------
    # 知识库统计
    # -------------------------------------------------------------------------

    async def get_knowledge_base_stats(
        self,
        kb_id: str,
        tenant_id: str,
    ) -> KnowledgeBaseStatsResponse:
        """获取知识库统计信息"""
        # 验证知识库存在
        kb = await self.get_knowledge_base(kb_id, tenant_id)

        # 统计文档数量（按状态分类）
        doc_stats_result = await self.db.execute(
            select(
                func.count(Document.id).label("total"),
                func.count(
                    case((Document.status == "published", 1), else_=None)
                ).label("published"),
                func.count(
                    case((Document.status == "processing", 1), else_=None)
                ).label("processing"),
                func.count(
                    case((Document.status == "failed", 1), else_=None)
                ).label("failed"),
            ).where(
                Document.knowledge_base_id == kb_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc_stats = doc_stats_result.one()

        # 统计Chunk
        chunk_result = await self.db.execute(
            select(
                func.count(DocumentChunk.id).label("total"),
                func.coalesce(func.sum(DocumentChunk.token_count), 0).label("total_tokens"),
                func.count(
                    case((DocumentChunk.index_status == "indexed", 1), else_=None)
                ).label("indexed"),
            ).where(
                DocumentChunk.knowledge_base_id == kb_id,
                DocumentChunk.tenant_id == tenant_id,
            )
        )
        chunk_stats = chunk_result.one()

        # 统计索引任务
        task_result = await self.db.execute(
            select(
                func.count(
                    case((IndexTask.status == "pending", 1), else_=None)
                ).label("pending"),
                func.count(
                    case((IndexTask.status == "failed", 1), else_=None)
                ).label("failed"),
            ).where(
                IndexTask.tenant_id == tenant_id,
            )
        )
        task_stats = task_result.one()

        return KnowledgeBaseStatsResponse(
            knowledge_base_id=kb_id,
            document_count=doc_stats.total or 0,
            published_count=doc_stats.published or 0,
            processing_count=doc_stats.processing or 0,
            failed_count=doc_stats.failed or 0,
            chunk_count=chunk_stats.total or 0,
            indexed_chunk_count=chunk_stats.indexed or 0,
            total_tokens=chunk_stats.total_tokens or 0,
            index_task_pending=task_stats.pending or 0,
            index_task_failed=task_stats.failed or 0,
        )

    # -------------------------------------------------------------------------
    # 知识库权限管理
    # -------------------------------------------------------------------------

    async def create_permission(
        self,
        kb_id: str,
        tenant_id: str,
        user_id: str,
        data: KnowledgeBasePermissionCreate,
    ) -> KnowledgeBasePermission:
        """配置知识库权限"""
        # 验证知识库存在
        await self.get_knowledge_base(kb_id, tenant_id)

        perm = KnowledgeBasePermission(
            tenant_id=tenant_id,
            knowledge_base_id=kb_id,
            principal_type=data.principal_type,
            principal_id=data.principal_id,
            permission_type=data.permission_type,
            is_deny=data.is_deny,
            effective_time=data.effective_time,
            expiration_time=data.expiration_time,
            created_by=user_id,
        )
        self.db.add(perm)
        await self.db.flush()
        return perm

    async def list_permissions(
        self,
        kb_id: str,
        tenant_id: str,
    ) -> list[KnowledgeBasePermission]:
        """查询知识库权限列表"""
        await self.get_knowledge_base(kb_id, tenant_id)

        result = await self.db.execute(
            select(KnowledgeBasePermission).where(
                KnowledgeBasePermission.knowledge_base_id == kb_id,
                KnowledgeBasePermission.tenant_id == tenant_id,
            ).order_by(KnowledgeBasePermission.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_permission(
        self,
        perm_id: str,
        tenant_id: str,
    ) -> None:
        """删除知识库权限"""
        result = await self.db.execute(
            select(KnowledgeBasePermission).where(
                KnowledgeBasePermission.id == perm_id,
                KnowledgeBasePermission.tenant_id == tenant_id,
            )
        )
        perm = result.scalar_one_or_none()
        if perm is None:
            raise ResourceNotFoundError(resource_type="权限配置", resource_id=perm_id)

        await self.db.delete(perm)
        await self.db.flush()
