"""
成员4：组织管理服务
实现用户、部门、用户组的CRUD和关系管理
"""
import uuid
from typing import Any, Sequence

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.identity import Department, UserGroup, user_departments, user_group_members
from app.models.user import User
from app.schemas.common import PaginatedData
from app.schemas.identity import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentTreeResponse,
    DepartmentUpdate,
    UserGroupCreate,
    UserGroupResponse,
    UserGroupUpdate,
)

logger = get_logger(__name__)


# ============ 部门服务 ============

async def create_department(
    db: AsyncSession,
    create_data: DepartmentCreate,
    current_user_id: str,
) -> DepartmentResponse:
    """创建部门"""
    existing = await db.execute(
        select(Department).filter(Department.code == create_data.code)
    )
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="部门", identifier=create_data.code)

    department = Department(
        id=f"dept_{uuid.uuid4().hex[:16]}",
        tenant_id="default",
        name=create_data.name,
        code=create_data.code,
        parent_id=create_data.parent_id,
        description=create_data.description,
        sort_order=create_data.sort_order,
        status="active",
        created_by=current_user_id,
    )
    db.add(department)
    await db.flush()

    logger.info("department_created", department_id=department.id, code=department.code)

    return DepartmentResponse.model_validate(department)


async def get_department_by_id(db: AsyncSession, department_id: str) -> Department | None:
    """根据ID获取部门"""
    result = await db.execute(
        select(Department).filter(
            and_(
                Department.id == department_id,
                Department.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_department_by_code(db: AsyncSession, code: str) -> Department | None:
    """根据编码获取部门"""
    result = await db.execute(
        select(Department).filter(
            and_(
                Department.code == code,
                Department.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def list_departments(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
) -> PaginatedData[DepartmentResponse]:
    """获取部门列表"""
    query = select(Department).filter(Department.deleted_at.is_(None))

    if keyword:
        query = query.filter(
            (Department.name.ilike(f"%{keyword}%")) | (Department.code.ilike(f"%{keyword}%"))
        )

    if status:
        query = query.filter(Department.status == status)

    count_query = select(func.count(Department.id)).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = query.order_by(Department.sort_order, Department.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    departments = result.scalars().all()

    items = []
    for dept in departments:
        dept_response = DepartmentResponse.model_validate(dept)
        
        if dept.parent_id:
            parent = await get_department_by_id(db, dept.parent_id)
            if parent:
                dept_response.parent_name = parent.name
        
        member_count_result = await db.execute(
            select(func.count(user_departments.c.user_id)).filter(user_departments.c.department_id == dept.id)
        )
        dept_response.member_count = member_count_result.scalar_one()
        
        items.append(dept_response)

    return PaginatedData.create(items, total, page, page_size)


async def build_department_tree(
    db: AsyncSession,
    parent_id: str | None = None,
) -> list[DepartmentTreeResponse]:
    """构建部门树"""
    result = await db.execute(
        select(Department)
        .filter(
            and_(
                Department.parent_id == parent_id,
                Department.deleted_at.is_(None),
                Department.status == "active",
            )
        )
        .order_by(Department.sort_order)
    )
    departments = result.scalars().all()

    tree = []
    for dept in departments:
        response = DepartmentTreeResponse.model_validate(dept)
        response.children = await build_department_tree(db, dept.id)
        tree.append(response)

    return tree


async def update_department(
    db: AsyncSession,
    department_id: str,
    update_data: DepartmentUpdate,
    current_user_id: str,
) -> DepartmentResponse:
    """更新部门"""
    department = await get_department_by_id(db, department_id)
    if not department:
        raise ResourceNotFoundError(resource_type="部门", resource_id=department_id)

    if update_data.code and update_data.code != department.code:
        existing = await get_department_by_code(db, update_data.code)
        if existing:
            raise DuplicateResourceError(resource_type="部门", identifier=update_data.code)

    if update_data.name is not None:
        department.name = update_data.name
    if update_data.code is not None:
        department.code = update_data.code
    if update_data.parent_id is not None:
        if update_data.parent_id == department.id:
            raise ValidationError(message="不能将部门设置为自己的父部门")
        department.parent_id = update_data.parent_id
    if update_data.description is not None:
        department.description = update_data.description
    if update_data.status is not None:
        department.status = update_data.status
    if update_data.sort_order is not None:
        department.sort_order = update_data.sort_order

    department.updated_by = current_user_id
    await db.flush()

    logger.info("department_updated", department_id=department.id)

    return DepartmentResponse.model_validate(department)


async def delete_department(db: AsyncSession, department_id: str, current_user_id: str) -> None:
    """删除部门"""
    department = await get_department_by_id(db, department_id)
    if not department:
        raise ResourceNotFoundError(resource_type="部门", resource_id=department_id)

    result = await db.execute(
        select(Department).filter(Department.parent_id == department_id)
    )
    children = result.scalars().all()
    if children:
        raise ValidationError(message="该部门存在子部门，无法删除")

    department.deleted_at = func.now()
    department.deleted_by = current_user_id
    await db.flush()

    logger.info("department_deleted", department_id=department_id)


# ============ 用户组服务 ============

async def create_user_group(
    db: AsyncSession,
    create_data: UserGroupCreate,
    current_user_id: str,
) -> UserGroupResponse:
    """创建用户组"""
    existing = await db.execute(
        select(UserGroup).filter(UserGroup.code == create_data.code)
    )
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="用户组", identifier=create_data.code)

    user_group = UserGroup(
        id=f"grp_{uuid.uuid4().hex[:16]}",
        tenant_id="default",
        name=create_data.name,
        code=create_data.code,
        description=create_data.description,
        status="active",
        created_by=current_user_id,
    )
    db.add(user_group)
    await db.flush()

    logger.info("user_group_created", group_id=user_group.id, code=user_group.code)

    return UserGroupResponse.model_validate(user_group)


async def get_user_group_by_id(db: AsyncSession, group_id: str) -> UserGroup | None:
    """根据ID获取用户组"""
    result = await db.execute(
        select(UserGroup).filter(
            and_(
                UserGroup.id == group_id,
                UserGroup.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_user_group_by_code(db: AsyncSession, code: str) -> UserGroup | None:
    """根据编码获取用户组"""
    result = await db.execute(
        select(UserGroup).filter(
            and_(
                UserGroup.code == code,
                UserGroup.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def list_user_groups(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
) -> PaginatedData[UserGroupResponse]:
    """获取用户组列表"""
    query = select(UserGroup).filter(UserGroup.deleted_at.is_(None))

    if keyword:
        query = query.filter(
            (UserGroup.name.ilike(f"%{keyword}%")) | (UserGroup.code.ilike(f"%{keyword}%"))
        )

    if status:
        query = query.filter(UserGroup.status == status)

    count_query = select(func.count(UserGroup.id)).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = query.order_by(UserGroup.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    groups = result.scalars().all()

    items = []
    for group in groups:
        group_response = UserGroupResponse.model_validate(group)
        
        member_count_result = await db.execute(
            select(func.count(user_group_members.c.user_id)).filter(user_group_members.c.group_id == group.id)
        )
        group_response.member_count = member_count_result.scalar_one()
        
        items.append(group_response)

    return PaginatedData.create(items, total, page, page_size)


async def update_user_group(
    db: AsyncSession,
    group_id: str,
    update_data: UserGroupUpdate,
    current_user_id: str,
) -> UserGroupResponse:
    """更新用户组"""
    user_group = await get_user_group_by_id(db, group_id)
    if not user_group:
        raise ResourceNotFoundError(resource_type="用户组", resource_id=group_id)

    if update_data.code and update_data.code != user_group.code:
        existing = await get_user_group_by_code(db, update_data.code)
        if existing:
            raise DuplicateResourceError(resource_type="用户组", identifier=update_data.code)

    if update_data.name is not None:
        user_group.name = update_data.name
    if update_data.code is not None:
        user_group.code = update_data.code
    if update_data.description is not None:
        user_group.description = update_data.description
    if update_data.status is not None:
        user_group.status = update_data.status

    user_group.updated_by = current_user_id
    await db.flush()

    logger.info("user_group_updated", group_id=group_id)

    return UserGroupResponse.model_validate(user_group)


async def delete_user_group(db: AsyncSession, group_id: str, current_user_id: str) -> None:
    """删除用户组"""
    user_group = await get_user_group_by_id(db, group_id)
    if not user_group:
        raise ResourceNotFoundError(resource_type="用户组", resource_id=group_id)

    user_group.deleted_at = func.now()
    user_group.deleted_by = current_user_id
    await db.flush()

    logger.info("user_group_deleted", group_id=group_id)


# ============ 用户组织关系服务 ============

async def assign_user_to_department(
    db: AsyncSession,
    user_id: str,
    department_id: str,
    is_primary: bool = False,
    current_user_id: str = "system",
) -> None:
    """分配用户到部门"""
    user = await db.execute(select(User).filter(User.id == user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise ResourceNotFoundError(resource_type="用户", resource_id=user_id)

    department = await get_department_by_id(db, department_id)
    if not department:
        raise ResourceNotFoundError(resource_type="部门", resource_id=department_id)

    existing = await db.execute(
        select(user_departments).filter(
            and_(
                user_departments.c.user_id == user_id,
                user_departments.c.department_id == department_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="用户部门关系", identifier=f"{user_id}-{department_id}")

    await db.execute(
        user_departments.insert().values(
            user_id=user_id,
            department_id=department_id,
            is_primary=is_primary,
        )
    )
    await db.flush()

    logger.info("user_assigned_to_department", user_id=user_id, department_id=department_id)


async def remove_user_from_department(db: AsyncSession, user_id: str, department_id: str) -> None:
    """从部门移除用户"""
    await db.execute(
        delete(user_departments).filter(
            and_(
                user_departments.c.user_id == user_id,
                user_departments.c.department_id == department_id,
            )
        )
    )
    await db.flush()

    logger.info("user_removed_from_department", user_id=user_id, department_id=department_id)


async def add_user_to_group(db: AsyncSession, user_id: str, group_id: str) -> None:
    """添加用户到用户组"""
    user = await db.execute(select(User).filter(User.id == user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise ResourceNotFoundError(resource_type="用户", resource_id=user_id)

    user_group = await get_user_group_by_id(db, group_id)
    if not user_group:
        raise ResourceNotFoundError(resource_type="用户组", resource_id=group_id)

    existing = await db.execute(
        select(user_group_members).filter(
            and_(
                user_group_members.c.user_id == user_id,
                user_group_members.c.group_id == group_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="用户组成员关系", identifier=f"{user_id}-{group_id}")

    await db.execute(
        user_group_members.insert().values(user_id=user_id, group_id=group_id)
    )
    await db.flush()

    logger.info("user_added_to_group", user_id=user_id, group_id=group_id)


async def remove_user_from_group(db: AsyncSession, user_id: str, group_id: str) -> None:
    """从用户组移除用户"""
    await db.execute(
        delete(user_group_members).filter(
            and_(
                user_group_members.c.user_id == user_id,
                user_group_members.c.group_id == group_id,
            )
        )
    )
    await db.flush()

    logger.info("user_removed_from_group", user_id=user_id, group_id=group_id)


async def get_user_departments(db: AsyncSession, user_id: str) -> list[Department]:
    """获取用户所属部门"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.departments))
        .filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return []
    return user.departments


async def get_user_groups(db: AsyncSession, user_id: str) -> list[UserGroup]:
    """获取用户所属用户组"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.groups))
        .filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return []
    return user.groups