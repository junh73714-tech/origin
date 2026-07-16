"""
成员4：RBAC服务
实现角色、权限、用户角色、角色权限的管理
"""
import uuid
from typing import Any, Sequence

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.auth import Permission, Role, role_permissions, user_roles
from app.models.user import User
from app.schemas.common import PaginatedData
from app.schemas.identity import DataScopeCreate, DataScopeResponse
from app.schemas.auth import RoleResponse, PermissionResponse

logger = get_logger(__name__)


# ============ 权限服务 ============

async def create_permission(
    db: AsyncSession,
    name: str,
    code: str,
    resource_type: str,
    action: str,
    description: str | None = None,
    created_by: str = "system",
) -> PermissionResponse:
    """创建权限"""
    existing = await db.execute(select(Permission).filter(Permission.code == code))
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="权限", identifier=code)

    permission = Permission(
        id=f"perm_{uuid.uuid4().hex[:16]}",
        tenant_id="default",
        name=name,
        code=code,
        resource_type=resource_type,
        action=action,
        description=description,
        created_by=created_by,
    )
    db.add(permission)
    await db.flush()

    logger.info("permission_created", permission_id=permission.id, code=code)

    return PermissionResponse.model_validate(permission)


async def get_permission_by_id(db: AsyncSession, permission_id: str) -> Permission | None:
    """根据ID获取权限"""
    result = await db.execute(
        select(Permission).filter(
            and_(
                Permission.id == permission_id,
                Permission.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_permission_by_code(db: AsyncSession, code: str) -> Permission | None:
    """根据编码获取权限"""
    result = await db.execute(
        select(Permission).filter(
            and_(
                Permission.code == code,
                Permission.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def list_permissions(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    resource_type: str | None = None,
) -> PaginatedData[PermissionResponse]:
    """获取权限列表"""
    query = select(Permission).filter(Permission.deleted_at.is_(None))

    if keyword:
        query = query.filter(
            (Permission.name.ilike(f"%{keyword}%")) | (Permission.code.ilike(f"%{keyword}%"))
        )

    if resource_type:
        query = query.filter(Permission.resource_type == resource_type)

    count_query = select(func.count(Permission.id)).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = query.order_by(Permission.code)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    permissions = result.scalars().all()

    items = [PermissionResponse.model_validate(p) for p in permissions]

    return PaginatedData.create(items, total, page, page_size)


async def update_permission(
    db: AsyncSession,
    permission_id: str,
    name: str | None = None,
    code: str | None = None,
    description: str | None = None,
    updated_by: str = "system",
) -> PermissionResponse:
    """更新权限"""
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise ResourceNotFoundError(resource_type="权限", resource_id=permission_id)

    if permission.is_system:
        raise ValidationError(message="系统权限不能修改")

    if code and code != permission.code:
        existing = await get_permission_by_code(db, code)
        if existing:
            raise DuplicateResourceError(resource_type="权限", identifier=code)
        permission.code = code

    if name is not None:
        permission.name = name
    if description is not None:
        permission.description = description

    permission.updated_by = updated_by
    await db.flush()

    logger.info("permission_updated", permission_id=permission_id)

    return PermissionResponse.model_validate(permission)


async def delete_permission(db: AsyncSession, permission_id: str, deleted_by: str = "system") -> None:
    """删除权限"""
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise ResourceNotFoundError(resource_type="权限", resource_id=permission_id)

    if permission.is_system:
        raise ValidationError(message="系统权限不能删除")

    result = await db.execute(
        select(role_permissions).filter(role_permissions.permission_id == permission_id)
    )
    if result.scalars().first():
        raise ValidationError(message="该权限已被角色引用，无法删除")

    permission.deleted_at = func.now()
    permission.deleted_by = deleted_by
    await db.flush()

    logger.info("permission_deleted", permission_id=permission_id)


# ============ 角色服务 ============

async def create_role(
    db: AsyncSession,
    name: str,
    code: str,
    description: str | None = None,
    is_system: bool = False,
    created_by: str = "system",
) -> RoleResponse:
    """创建角色"""
    existing = await db.execute(select(Role).filter(Role.code == code))
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="角色", identifier=code)

    role = Role(
        id=f"role_{uuid.uuid4().hex[:16]}",
        tenant_id="default",
        name=name,
        code=code,
        description=description,
        is_system=is_system,
        created_by=created_by,
    )
    db.add(role)
    await db.flush()

    logger.info("role_created", role_id=role.id, code=code, is_system=is_system)

    return RoleResponse.model_validate(role)


async def get_role_by_id(db: AsyncSession, role_id: str) -> Role | None:
    """根据ID获取角色"""
    result = await db.execute(
        select(Role).filter(
            and_(
                Role.id == role_id,
                Role.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_role_by_code(db: AsyncSession, code: str) -> Role | None:
    """根据编码获取角色"""
    result = await db.execute(
        select(Role).filter(
            and_(
                Role.code == code,
                Role.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def list_roles(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> PaginatedData[RoleResponse]:
    """获取角色列表"""
    query = select(Role).filter(Role.deleted_at.is_(None))

    if keyword:
        query = query.filter(
            (Role.name.ilike(f"%{keyword}%")) | (Role.code.ilike(f"%{keyword}%"))
        )

    count_query = select(func.count(Role.id)).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = query.order_by(Role.is_system.desc(), Role.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    roles = result.scalars().all()

    items = [RoleResponse.model_validate(r) for r in roles]

    return PaginatedData.create(items, total, page, page_size)


async def get_role_with_permissions(db: AsyncSession, role_id: str) -> Role | None:
    """获取角色及其权限"""
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .filter(
            and_(
                Role.id == role_id,
                Role.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def update_role(
    db: AsyncSession,
    role_id: str,
    name: str | None = None,
    code: str | None = None,
    description: str | None = None,
    updated_by: str = "system",
) -> RoleResponse:
    """更新角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ResourceNotFoundError(resource_type="角色", resource_id=role_id)

    if role.is_system:
        raise ValidationError(message="系统角色不能修改")

    if code and code != role.code:
        existing = await get_role_by_code(db, code)
        if existing:
            raise DuplicateResourceError(resource_type="角色", identifier=code)
        role.code = code

    if name is not None:
        role.name = name
    if description is not None:
        role.description = description

    role.updated_by = updated_by
    await db.flush()

    logger.info("role_updated", role_id=role_id)

    return RoleResponse.model_validate(role)


async def delete_role(db: AsyncSession, role_id: str, deleted_by: str = "system") -> None:
    """删除角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ResourceNotFoundError(resource_type="角色", resource_id=role_id)

    if role.is_system:
        raise ValidationError(message="系统角色不能删除")

    result = await db.execute(select(user_roles).filter(user_roles.role_id == role_id))
    if result.scalars().first():
        raise ValidationError(message="该角色已被用户引用，无法删除")

    role.deleted_at = func.now()
    role.deleted_by = deleted_by
    await db.flush()

    logger.info("role_deleted", role_id=role_id)


# ============ 用户角色服务 ============

async def assign_role_to_user(db: AsyncSession, user_id: str, role_id: str) -> None:
    """分配角色给用户"""
    user = await db.execute(select(User).filter(User.id == user_id))
    user = user.scalar_one_or_none()
    if not user:
        raise ResourceNotFoundError(resource_type="用户", resource_id=user_id)

    role = await get_role_by_id(db, role_id)
    if not role:
        raise ResourceNotFoundError(resource_type="角色", resource_id=role_id)

    existing = await db.execute(
        select(user_roles).filter(
            and_(
                user_roles.user_id == user_id,
                user_roles.role_id == role_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="用户角色关系", identifier=f"{user_id}-{role_id}")

    await db.execute(
        user_roles.__table__.insert().values(user_id=user_id, role_id=role_id)
    )
    await db.flush()

    logger.info("role_assigned_to_user", user_id=user_id, role_id=role_id)


async def remove_role_from_user(db: AsyncSession, user_id: str, role_id: str) -> None:
    """从用户移除角色"""
    await db.execute(
        delete(user_roles).filter(
            and_(
                user_roles.user_id == user_id,
                user_roles.role_id == role_id,
            )
        )
    )
    await db.flush()

    logger.info("role_removed_from_user", user_id=user_id, role_id=role_id)


async def get_user_roles(db: AsyncSession, user_id: str) -> list[Role]:
    """获取用户角色"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return []
    return user.roles


async def get_user_permissions(db: AsyncSession, user_id: str) -> list[Permission]:
    """获取用户权限"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return []

    permissions = []
    seen = set()
    for role in user.roles:
        for permission in role.permissions:
            if permission.id not in seen:
                seen.add(permission.id)
                permissions.append(permission)

    return permissions


# ============ 角色权限服务 ============

async def assign_permission_to_role(db: AsyncSession, role_id: str, permission_id: str) -> None:
    """分配权限给角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ResourceNotFoundError(resource_type="角色", resource_id=role_id)

    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise ResourceNotFoundError(resource_type="权限", resource_id=permission_id)

    existing = await db.execute(
        select(role_permissions).filter(
            and_(
                role_permissions.role_id == role_id,
                role_permissions.permission_id == permission_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="角色权限关系", identifier=f"{role_id}-{permission_id}")

    await db.execute(
        role_permissions.__table__.insert().values(role_id=role_id, permission_id=permission_id)
    )
    await db.flush()

    logger.info("permission_assigned_to_role", role_id=role_id, permission_id=permission_id)


async def remove_permission_from_role(db: AsyncSession, role_id: str, permission_id: str) -> None:
    """从角色移除权限"""
    await db.execute(
        delete(role_permissions).filter(
            and_(
                role_permissions.role_id == role_id,
                role_permissions.permission_id == permission_id,
            )
        )
    )
    await db.flush()

    logger.info("permission_removed_from_role", role_id=role_id, permission_id=permission_id)


async def get_role_permissions(db: AsyncSession, role_id: str) -> list[Permission]:
    """获取角色权限"""
    role = await get_role_with_permissions(db, role_id)
    if not role:
        return []
    return role.permissions


# ============ 数据范围服务 ============

async def create_data_scope(
    db: AsyncSession,
    create_data: DataScopeCreate,
    created_by: str = "system",
) -> DataScopeResponse:
    """创建数据范围"""
    existing = await db.execute(
        select(Permission).filter(Permission.code == create_data.code)
    )
    if existing.scalar_one_or_none():
        raise DuplicateResourceError(resource_type="数据范围", identifier=create_data.code)

    from app.models.identity import DataScope
    data_scope = DataScope(
        id=f"scope_{uuid.uuid4().hex[:16]}",
        tenant_id="default",
        name=create_data.name,
        code=create_data.code,
        scope_type=create_data.scope_type,
        description=create_data.description,
        status="active",
        created_by=created_by,
    )
    db.add(data_scope)
    await db.flush()

    logger.info("data_scope_created", scope_id=data_scope.id, code=create_data.code)

    return DataScopeResponse.model_validate(data_scope)


async def list_data_scopes(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedData[DataScopeResponse]:
    """获取数据范围列表"""
    from app.models.identity import DataScope
    query = select(DataScope).filter(DataScope.deleted_at.is_(None))

    count_query = select(func.count(DataScope.id)).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = query.order_by(DataScope.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    scopes = result.scalars().all()

    items = [DataScopeResponse.model_validate(s) for s in scopes]

    return PaginatedData.create(items, total, page, page_size)


async def can_execute_action(db: AsyncSession, user_id: str, action: str) -> bool:
    """检查用户是否可以执行指定操作"""
    permissions = await get_user_permissions(db, user_id)
    permission_codes = {p.code for p in permissions}

    if "*" in permission_codes:
        return True

    return action in permission_codes