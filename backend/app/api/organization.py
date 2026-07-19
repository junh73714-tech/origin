"""
成员4：组织管理路由
实现部门、用户组、用户组织关系的管理接口
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DBSession, RequiredUser
from app.core.responses import paginated_response, success_response
from app.schemas.common import PaginationParams
from app.schemas.identity import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentUpdate,
    UserDepartmentAssign,
    UserGroupCreate,
    UserGroupMemberAdd,
    UserGroupResponse,
    UserGroupUpdate,
)
from app.services.organization_service import (
    add_user_to_group,
    assign_user_to_department,
    create_department,
    create_user_group,
    delete_department,
    delete_user_group,
    get_user_departments,
    get_user_groups,
    list_departments,
    list_user_groups,
    remove_user_from_department,
    remove_user_from_group,
    update_department,
    update_user_group,
    build_department_tree,
)

organization_router = APIRouter()
router = organization_router  # main.py 兼容别名


# ============ 部门路由 ============

@organization_router.post("/departments", response_model=DepartmentResponse, tags=["组织管理"])
async def create_department_api(
    create_data: DepartmentCreate,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """创建部门"""
    result = await create_department(db, create_data, current_user_id)
    return result


@organization_router.get("/departments", tags=["组织管理"])
async def list_departments_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """获取部门列表"""
    result = await list_departments(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        keyword=keyword,
        status=status,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@organization_router.get("/departments/tree", response_model=list[DepartmentTreeResponse], tags=["组织管理"])
async def get_department_tree_api(db: DBSession):
    """获取部门树形结构"""
    result = await build_department_tree(db)
    return result


@organization_router.get("/departments/{department_id}", response_model=DepartmentResponse, tags=["组织管理"])
async def get_department_api(department_id: str, db: DBSession):
    """获取部门详情"""
    from app.services.organization_service import get_department_by_id
    department = await get_department_by_id(db, department_id)
    if not department:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource_type="部门", resource_id=department_id)
    return DepartmentResponse.model_validate(department)


@organization_router.put("/departments/{department_id}", response_model=DepartmentResponse, tags=["组织管理"])
async def update_department_api(
    department_id: str,
    update_data: DepartmentUpdate,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """更新部门"""
    result = await update_department(db, department_id, update_data, current_user_id)
    return result


@organization_router.delete("/departments/{department_id}", tags=["组织管理"])
async def delete_department_api(
    department_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """删除部门"""
    await delete_department(db, department_id, current_user_id)
    return success_response(message="删除成功")


# ============ 用户组路由 ============

@organization_router.post("/user-groups", response_model=UserGroupResponse, tags=["组织管理"])
async def create_user_group_api(
    create_data: UserGroupCreate,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """创建用户组"""
    result = await create_user_group(db, create_data, current_user_id)
    return result


@organization_router.get("/user-groups", tags=["组织管理"])
async def list_user_groups_api(
    db: DBSession,
    pagination: Annotated[PaginationParams, Depends()],
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """获取用户组列表"""
    result = await list_user_groups(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        keyword=keyword,
        status=status,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@organization_router.get("/user-groups/{group_id}", response_model=UserGroupResponse, tags=["组织管理"])
async def get_user_group_api(group_id: str, db: DBSession):
    """获取用户组详情"""
    from app.services.organization_service import get_user_group_by_id
    user_group = await get_user_group_by_id(db, group_id)
    if not user_group:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource_type="用户组", resource_id=group_id)
    return UserGroupResponse.model_validate(user_group)


@organization_router.put("/user-groups/{group_id}", response_model=UserGroupResponse, tags=["组织管理"])
async def update_user_group_api(
    group_id: str,
    update_data: UserGroupUpdate,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """更新用户组"""
    result = await update_user_group(db, group_id, update_data, current_user_id)
    return result


@organization_router.delete("/user-groups/{group_id}", tags=["组织管理"])
async def delete_user_group_api(
    group_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """删除用户组"""
    await delete_user_group(db, group_id, current_user_id)
    return success_response(message="删除成功")


# ============ 用户组织关系路由 ============

@organization_router.post("/departments/{department_id}/users", tags=["组织管理"])
async def assign_user_to_department_api(
    department_id: str,
    data: UserDepartmentAssign,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """分配用户到部门"""
    await assign_user_to_department(
        db, data.user_id, department_id, data.is_primary, current_user_id
    )
    return success_response(message="分配成功")


@organization_router.delete("/departments/{department_id}/users/{user_id}", tags=["组织管理"])
async def remove_user_from_department_api(
    department_id: str,
    user_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """从部门移除用户"""
    await remove_user_from_department(db, user_id, department_id)
    return success_response(message="移除成功")


@organization_router.post("/user-groups/{group_id}/members", tags=["组织管理"])
async def add_user_to_group_api(
    group_id: str,
    data: UserGroupMemberAdd,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """添加用户到用户组"""
    await add_user_to_group(db, data.user_id, group_id)
    return success_response(message="添加成功")


@organization_router.delete("/user-groups/{group_id}/members/{user_id}", tags=["组织管理"])
async def remove_user_from_group_api(
    group_id: str,
    user_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """从用户组移除用户"""
    await remove_user_from_group(db, user_id, group_id)
    return success_response(message="移除成功")


@organization_router.get("/users/{user_id}/departments", response_model=list[DepartmentResponse], tags=["组织管理"])
async def get_user_departments_api(user_id: str, db: DBSession):
    """获取用户所属部门"""
    departments = await get_user_departments(db, user_id)
    return [DepartmentResponse.model_validate(d) for d in departments]


@organization_router.get("/users/{user_id}/groups", response_model=list[UserGroupResponse], tags=["组织管理"])
async def get_user_groups_api(user_id: str, db: DBSession):
    """获取用户所属用户组"""
    groups = await get_user_groups(db, user_id)
    return [UserGroupResponse.model_validate(g) for g in groups]