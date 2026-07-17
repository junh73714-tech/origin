"""
知识库路由

提供知识库 CRUD、启用/停用、统计和权限管理 API。

成员5主责：知识库相关全部端点
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, DBSession
from app.core.responses import success_response, paginated_response
from app.schemas.common import PaginationParams
from app.schemas.document import (
    KnowledgeBaseCreate,
    KnowledgeBaseDetailResponse,
    KnowledgeBaseListParams,
    KnowledgeBasePermissionCreate,
    KnowledgeBasePermissionResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseStatsResponse,
    KnowledgeBaseUpdate,
)
from app.services.knowledge_base import KnowledgeBaseService

router = APIRouter()
knowledge_bases_router = router


def get_kb_service(db: DBSession) -> KnowledgeBaseService:
    """依赖注入：获取知识库服务实例"""
    return KnowledgeBaseService(db)


# =============================================================================
# 知识库 CRUD
# =============================================================================

@router.post("", summary="创建知识库")
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: DBSession,
    user_id: CurrentUser = "system",
):
    """创建新的知识库"""
    service = KnowledgeBaseService(db)
    kb = await service.create_knowledge_base(
        tenant_id="default",
        user_id=user_id or "system",
        data=data,
    )
    return success_response(
        data=KnowledgeBaseResponse.model_validate(kb),
        message="知识库创建成功",
    )


@router.get("", summary="知识库列表")
async def list_knowledge_bases(
    db: DBSession,
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """获取知识库列表（分页+搜索+状态筛选）"""
    service = KnowledgeBaseService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await service.list_knowledge_bases(
        tenant_id="default",
        pagination=pagination,
        keyword=keyword,
        status=status,
    )
    return paginated_response(
        items=[KnowledgeBaseResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="查询成功",
    )


@router.get("/{kb_id}", summary="知识库详情")
async def get_knowledge_base(
    kb_id: str,
    db: DBSession,
):
    """获取知识库详细信息"""
    service = KnowledgeBaseService(db)
    kb = await service.get_knowledge_base(kb_id, tenant_id="default")
    return success_response(
        data=KnowledgeBaseDetailResponse.model_validate(kb),
        message="查询成功",
    )


@router.put("/{kb_id}", summary="编辑知识库")
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    db: DBSession,
):
    """编辑知识库信息"""
    service = KnowledgeBaseService(db)
    kb = await service.update_knowledge_base(kb_id, tenant_id="default", data=data)
    return success_response(
        data=KnowledgeBaseResponse.model_validate(kb),
        message="知识库更新成功",
    )


# =============================================================================
# 知识库启停
# =============================================================================

@router.patch("/{kb_id}/enable", summary="启用知识库")
async def enable_knowledge_base(
    kb_id: str,
    db: DBSession,
):
    """启用知识库，恢复可检索状态"""
    service = KnowledgeBaseService(db)
    kb = await service.enable_knowledge_base(kb_id, tenant_id="default")
    return success_response(
        data=KnowledgeBaseResponse.model_validate(kb),
        message="知识库已启用",
    )


@router.patch("/{kb_id}/disable", summary="停用知识库")
async def disable_knowledge_base(
    kb_id: str,
    db: DBSession,
):
    """停用知识库，不允许新检索，不删除历史数据"""
    service = KnowledgeBaseService(db)
    kb = await service.disable_knowledge_base(kb_id, tenant_id="default")
    return success_response(
        data=KnowledgeBaseResponse.model_validate(kb),
        message="知识库已停用",
    )


# =============================================================================
# 知识库统计
# =============================================================================

@router.get("/{kb_id}/stats", summary="知识库统计")
async def get_knowledge_base_stats(
    kb_id: str,
    db: DBSession,
):
    """获取知识库统计信息（文档数量、Chunk数量、索引统计等）"""
    service = KnowledgeBaseService(db)
    stats = await service.get_knowledge_base_stats(kb_id, tenant_id="default")
    return success_response(
        data=stats,
        message="查询成功",
    )


# =============================================================================
# 知识库权限管理
# =============================================================================

@router.post("/{kb_id}/permissions", summary="配置知识库权限")
async def create_knowledge_base_permission(
    kb_id: str,
    data: KnowledgeBasePermissionCreate,
    db: DBSession,
    user_id: CurrentUser = "system",
):
    """为知识库配置权限"""
    service = KnowledgeBaseService(db)
    perm = await service.create_permission(
        kb_id=kb_id,
        tenant_id="default",
        user_id=user_id or "system",
        data=data,
    )
    return success_response(
        data=KnowledgeBasePermissionResponse.model_validate(perm),
        message="权限配置成功",
    )


@router.get("/{kb_id}/permissions", summary="查询知识库权限")
async def list_knowledge_base_permissions(
    kb_id: str,
    db: DBSession,
):
    """查询知识库的权限配置列表"""
    service = KnowledgeBaseService(db)
    perms = await service.list_permissions(kb_id, tenant_id="default")
    return success_response(
        data=[KnowledgeBasePermissionResponse.model_validate(p) for p in perms],
        message="查询成功",
    )


@router.delete(
    "/{kb_id}/permissions/{perm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除知识库权限",
)
async def delete_knowledge_base_permission(
    kb_id: str,
    perm_id: str,
    db: DBSession,
):
    """删除知识库的一条权限配置"""
    service = KnowledgeBaseService(db)
    await service.delete_permission(perm_id, tenant_id="default")
    return None
