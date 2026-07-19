"""
成员4：RBAC路由
实现角色、权限、用户角色、角色权限的管理接口
"""
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DBSession, RequiredUser
from app.core.responses import paginated_response, success_response
from app.schemas.common import PaginationParams
from app.schemas.auth import PermissionCreate, RoleCreate, RoleResponse, PermissionResponse
from app.schemas.identity import (
    DataScopeCreate,
    DataScopeResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
)
from app.services.rbac_service import (
    assign_permission_to_role,
    assign_role_to_user,
    can_execute_action,
    create_data_scope,
    create_permission,
    create_role,
    delete_permission,
    delete_role,
    get_permission_by_code,
    get_permission_by_id,
    get_role_by_code,
    get_role_by_id,
    get_role_permissions,
    get_user_permissions,
    get_user_roles,
    list_data_scopes,
    list_permissions,
    list_roles,
    remove_permission_from_role,
    remove_role_from_user,
    update_permission,
    update_role,
)

rbac_router = APIRouter()
router = rbac_router  # main.py 兼容别名
# ============ 权限路由 ============

@rbac_router.post("/permissions", response_model=PermissionResponse, tags=["RBAC"])
async def create_permission_api(
    create_data: PermissionCreate,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """创建权限"""
    result = await create_permission(
        db,
        create_data.name,
        create_data.code,
        create_data.resource_type,
        create_data.action,
        create_data.description,
        current_user_id,
    )
    return result


@rbac_router.get("/permissions", tags=["RBAC"])
async def list_permissions_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
    keyword: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
):
    """获取权限列表"""
    result = await list_permissions(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        keyword=keyword,
        resource_type=resource_type,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@rbac_router.get("/permissions/{permission_id}", response_model=PermissionResponse, tags=["RBAC"])
async def get_permission_api(permission_id: str, db: DBSession):
    """获取权限详情"""
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource_type="权限", resource_id=permission_id)
    return PermissionResponse.model_validate(permission)


@rbac_router.put("/permissions/{permission_id}", response_model=PermissionResponse, tags=["RBAC"])
async def update_permission_api(
    permission_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
    name: str | None = Query(default=None),
    code: str | None = Query(default=None),
    description: str | None = Query(default=None),
):
    """更新权限"""
    result = await update_permission(db, permission_id, name, code, description, current_user_id)
    return result


@rbac_router.delete("/permissions/{permission_id}", tags=["RBAC"])
async def delete_permission_api(
    permission_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """删除权限"""
    await delete_permission(db, permission_id, current_user_id)
    return success_response(message="删除成功")


# ============ 角色路由 ============

@rbac_router.post("/roles", response_model=RoleResponse, tags=["RBAC"])
async def create_role_api(
    create_data: RoleCreate,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """创建角色"""
    result = await create_role(
        db,
        create_data.name,
        create_data.code,
        create_data.description,
        create_data.is_system,
        current_user_id,
    )
    return result


@rbac_router.get("/roles", tags=["RBAC"])
async def list_roles_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
    keyword: str | None = Query(default=None),
):
    """获取角色列表"""
    result = await list_roles(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        keyword=keyword,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@rbac_router.get("/roles/{role_id}", response_model=RoleResponse, tags=["RBAC"])
async def get_role_api(role_id: str, db: DBSession):
    """获取角色详情"""
    from sqlalchemy import func, select
    from app.models.auth import user_roles
    
    role = await get_role_by_id(db, role_id)
    if not role:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource_type="角色", resource_id=role_id)
    
    role_response = RoleResponse.model_validate(role)
    role_response.permission_count = len(role.permissions)
    
    user_count_result = await db.execute(
        select(func.count(user_roles.user_id)).filter(user_roles.role_id == role_id)
    )
    role_response.user_count = user_count_result.scalar_one()
    
    return role_response


@rbac_router.get("/roles/{role_id}/permissions", response_model=list[PermissionResponse], tags=["RBAC"])
async def get_role_permissions_api(role_id: str, db: DBSession):
    """获取角色权限"""
    permissions = await get_role_permissions(db, role_id)
    return [PermissionResponse.model_validate(p) for p in permissions]


@rbac_router.put("/roles/{role_id}", response_model=RoleResponse, tags=["RBAC"])
async def update_role_api(
    role_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
    name: str | None = Query(default=None),
    code: str | None = Query(default=None),
    description: str | None = Query(default=None),
):
    """更新角色"""
    result = await update_role(db, role_id, name, code, description, current_user_id)
    return result


@rbac_router.delete("/roles/{role_id}", tags=["RBAC"])
async def delete_role_api(
    role_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """删除角色"""
    await delete_role(db, role_id, current_user_id)
    return success_response(message="删除成功")


# ============ 用户角色路由 ============

@rbac_router.post("/users/{user_id}/roles", tags=["RBAC"])
async def assign_role_to_user_api(
    user_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
    role_id: str = Query(...),
):
    """分配角色给用户"""
    await assign_role_to_user(db, user_id, role_id)
    return success_response(message="分配成功")


@rbac_router.delete("/users/{user_id}/roles/{role_id}", tags=["RBAC"])
async def remove_role_from_user_api(
    user_id: str,
    role_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """从用户移除角色"""
    await remove_role_from_user(db, user_id, role_id)
    return success_response(message="移除成功")


@rbac_router.get("/users/{user_id}/roles", response_model=list[RoleResponse], tags=["RBAC"])
async def get_user_roles_api(user_id: str, db: DBSession):
    """获取用户角色"""
    roles = await get_user_roles(db, user_id)
    return [RoleResponse.model_validate(r) for r in roles]


@rbac_router.get("/users/{user_id}/permissions", response_model=list[PermissionResponse], tags=["RBAC"])
async def get_user_permissions_api(user_id: str, db: DBSession):
    """获取用户权限"""
    permissions = await get_user_permissions(db, user_id)
    return [PermissionResponse.model_validate(p) for p in permissions]


# ============ 角色权限路由 ============

@rbac_router.post("/roles/{role_id}/permissions", tags=["RBAC"])
async def assign_permission_to_role_api(
    role_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
    permission_id: str = Query(...),
):
    """分配权限给角色"""
    await assign_permission_to_role(db, role_id, permission_id)
    return success_response(message="分配成功")


@rbac_router.delete("/roles/{role_id}/permissions/{permission_id}", tags=["RBAC"])
async def remove_permission_from_role_api(
    role_id: str,
    permission_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """从角色移除权限"""
    await remove_permission_from_role(db, role_id, permission_id)
    return success_response(message="移除成功")


# ============ 数据范围路由 ============

@rbac_router.post("/data-scopes", response_model=DataScopeResponse, tags=["RBAC"])
async def create_data_scope_api(
    create_data: DataScopeCreate,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """创建数据范围"""
    result = await create_data_scope(db, create_data, current_user_id)
    return result


@rbac_router.get("/data-scopes", tags=["RBAC"])
async def list_data_scopes_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
):
    """获取数据范围列表"""
    result = await list_data_scopes(db, page=pagination.page, page_size=pagination.page_size)
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


# ============ 权限检查路由 ============

@rbac_router.post("/permission-check", response_model=PermissionCheckResponse, tags=["RBAC"])
async def check_permission_api(
    check_data: PermissionCheckRequest,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """检查用户权限"""
    allowed = await can_execute_action(db, current_user_id, check_data.action)
    return PermissionCheckResponse(
        allowed=allowed,
        permission=check_data.action,
        resource_type=check_data.resource_type,
        resource_id=check_data.resource_id,
        reason="权限充足" if allowed else "权限不足",
    )