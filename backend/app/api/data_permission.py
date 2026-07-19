"""
成员4：数据权限路由
实现知识库权限、文档权限、临时授权的管理接口
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DBSession, RequiredUser
from app.core.responses import paginated_response, success_response
from app.schemas.common import PaginationParams
from app.schemas.identity import (
    DocumentPermissionCreate,
    DocumentPermissionResponse,
    KnowledgeBasePermissionCreate,
    KnowledgeBasePermissionResponse,
    TemporaryGrantCreate,
    TemporaryGrantResponse,
    TemporaryGrantUpdate,
)
from app.services.data_permission_service import DataPermissionService

data_permission_router = APIRouter()
router = data_permission_router  # main.py 兼容别名
# ============ 知识库权限路由 ============

@data_permission_router.post("/knowledge-base-permissions", response_model=KnowledgeBasePermissionResponse, tags=["数据权限"])
async def create_knowledge_base_permission_api(
    db: DBSession,
    current_user_id: RequiredUser,
    create_data: KnowledgeBasePermissionCreate,
):
    """创建知识库权限"""
    service = DataPermissionService(db)
    result = await service.create_knowledge_base_permission(create_data, current_user_id)
    return result


@data_permission_router.get("/knowledge-base-permissions", tags=["数据权限"])
async def list_knowledge_base_permissions_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
    knowledge_base_id: str | None = Query(default=None),
):
    """获取知识库权限列表"""
    service = DataPermissionService(db)
    result = await service.list_knowledge_base_permissions(
        knowledge_base_id=knowledge_base_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@data_permission_router.delete("/knowledge-base-permissions/{permission_id}", tags=["数据权限"])
async def delete_knowledge_base_permission_api(
    permission_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """删除知识库权限"""
    service = DataPermissionService(db)
    await service.delete_knowledge_base_permission(permission_id, current_user_id)
    return success_response(message="删除成功")


# ============ 文档权限路由 ============

@data_permission_router.post("/document-permissions", response_model=DocumentPermissionResponse, tags=["数据权限"])
async def create_document_permission_api(
    db: DBSession,
    current_user_id: RequiredUser,
    create_data: DocumentPermissionCreate,
):
    """创建文档权限"""
    service = DataPermissionService(db)
    result = await service.create_document_permission(create_data, current_user_id)
    return result


@data_permission_router.get("/document-permissions", tags=["数据权限"])
async def list_document_permissions_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
    document_id: str | None = Query(default=None),
):
    """获取文档权限列表"""
    service = DataPermissionService(db)
    result = await service.list_document_permissions(
        document_id=document_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@data_permission_router.delete("/document-permissions/{permission_id}", tags=["数据权限"])
async def delete_document_permission_api(
    permission_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """删除文档权限"""
    service = DataPermissionService(db)
    await service.delete_document_permission(permission_id, current_user_id)
    return success_response(message="删除成功")


# ============ 临时授权路由 ============

@data_permission_router.post("/temporary-grants", response_model=TemporaryGrantResponse, tags=["数据权限"])
async def create_temporary_grant_api(
    db: DBSession,
    current_user_id: RequiredUser,
    create_data: TemporaryGrantCreate,
):
    """创建临时授权"""
    service = DataPermissionService(db)
    result = await service.create_temporary_grant(create_data, current_user_id)
    return result


@data_permission_router.get("/temporary-grants", tags=["数据权限"])
async def list_temporary_grants_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
    user_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """获取临时授权列表"""
    service = DataPermissionService(db)
    result = await service.list_temporary_grants(
        user_id=user_id,
        status=status,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@data_permission_router.get("/temporary-grants/{grant_id}", response_model=TemporaryGrantResponse, tags=["数据权限"])
async def get_temporary_grant_api(grant_id: str, db: DBSession):
    """获取临时授权详情"""
    service = DataPermissionService(db)
    result = await service.get_temporary_grant(grant_id)
    if not result:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource_type="临时授权", resource_id=grant_id)
    return result


@data_permission_router.put("/temporary-grants/{grant_id}", response_model=TemporaryGrantResponse, tags=["数据权限"])
async def update_temporary_grant_api(
    grant_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
    update_data: TemporaryGrantUpdate,
):
    """更新临时授权"""
    service = DataPermissionService(db)
    result = await service.update_temporary_grant(grant_id, update_data, current_user_id)
    return result


@data_permission_router.delete("/temporary-grants/{grant_id}", tags=["数据权限"])
async def delete_temporary_grant_api(
    grant_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """删除临时授权"""
    service = DataPermissionService(db)
    await service.delete_temporary_grant(grant_id, current_user_id)
    return success_response(message="删除成功")


@data_permission_router.post("/temporary-grants/check-expired", tags=["数据权限"])
async def check_expired_grants_api(db: DBSession):
    """检查并处理过期临时授权"""
    service = DataPermissionService(db)
    expired_grants = await service.check_expired_grants()
    return success_response(
        data={"expired_count": len(expired_grants), "grant_ids": [g.id for g in expired_grants]},
        message=f"已处理 {len(expired_grants)} 个过期临时授权",
    )