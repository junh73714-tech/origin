"""
成员4：测试数据种子服务
创建两部门三角色的演示数据
"""
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.models.auth import Permission, Role
from app.models.identity import Department, UserGroup
from app.models.user import User
from app.services.rbac_service import (
    assign_permission_to_role,
    assign_role_to_user,
)
from app.services.organization_service import (
    assign_user_to_department,
    add_user_to_group,
)

logger = get_logger(__name__)


DEFAULT_PASSWORD = "Test@123456"


async def seed_test_data(db: AsyncSession) -> None:
    """创建测试数据"""
    logger.info("starting_seed_test_data")

    await create_tenant(db)
    await create_permissions(db)
    await create_roles(db)
    await create_departments(db)
    await create_user_groups(db)
    await create_users(db)
    await assign_user_roles(db)
    await assign_user_organizations(db)

    logger.info("seed_test_data_completed")


async def create_tenant(db: AsyncSession) -> None:
    """创建默认租户"""
    from app.models.document import Tenant
    existing = await db.execute(select(Tenant).filter(Tenant.id == "default"))
    if existing.scalar_one_or_none():
        return

    tenant = Tenant(
        id="default",
        name="默认租户",
        status="active",
        settings={},
        created_by="system",
    )
    db.add(tenant)
    await db.flush()
    logger.info("tenant_created", tenant_id="default")


async def create_permissions(db: AsyncSession) -> None:
    """创建权限"""
    permissions = [
        {"name": "用户读取", "code": "user.read", "resource_type": "user", "action": "read"},
        {"name": "用户管理", "code": "user.manage", "resource_type": "user", "action": "manage"},
        {"name": "角色管理", "code": "role.manage", "resource_type": "role", "action": "manage"},
        {"name": "知识库读取", "code": "knowledge_base.read", "resource_type": "knowledge_base", "action": "read"},
        {"name": "知识库管理", "code": "knowledge_base.manage", "resource_type": "knowledge_base", "action": "manage"},
        {"name": "文档上传", "code": "document.upload", "resource_type": "document", "action": "upload"},
        {"name": "文档发布", "code": "document.publish", "resource_type": "document", "action": "publish"},
        {"name": "文档读取", "code": "document.read", "resource_type": "document", "action": "read"},
        {"name": "标准问答审核", "code": "qa.review", "resource_type": "qa", "action": "review"},
        {"name": "评估任务", "code": "evaluation.run", "resource_type": "evaluation", "action": "run"},
        {"name": "审计读取", "code": "audit.read", "resource_type": "audit", "action": "read"},
        {"name": "系统配置", "code": "system.configure", "resource_type": "system", "action": "configure"},
    ]

    from app.services.rbac_service import create_permission

    for perm in permissions:
        existing = await db.execute(select(Permission).filter(Permission.code == perm["code"]))
        if not existing.scalar_one_or_none():
            await create_permission(
                db,
                name=perm["name"],
                code=perm["code"],
                resource_type=perm["resource_type"],
                action=perm["action"],
                created_by="system",
            )
            logger.info("permission_seeded", code=perm["code"])


async def create_roles(db: AsyncSession) -> None:
    """创建角色"""
    roles = [
        {
            "name": "系统管理员",
            "code": "super_admin",
            "description": "系统管理员，拥有所有管理权限",
            "is_system": True,
            "permissions": ["system.configure", "audit.read", "user.manage", "role.manage"],
        },
        {
            "name": "知识库管理员",
            "code": "knowledge_base_admin",
            "description": "知识库管理员，管理知识库和文档",
            "is_system": False,
            "permissions": ["knowledge_base.manage", "document.upload", "document.publish", "document.read"],
        },
        {
            "name": "普通用户",
            "code": "normal_user",
            "description": "普通用户，可读取知识库和文档",
            "is_system": False,
            "permissions": ["knowledge_base.read", "document.read"],
        },
    ]

    from app.services.rbac_service import create_role, get_permission_by_code

    for role_data in roles:
        existing = await db.execute(select(Role).filter(Role.code == role_data["code"]))
        if not existing.scalar_one_or_none():
            role = await create_role(
                db,
                name=role_data["name"],
                code=role_data["code"],
                description=role_data["description"],
                is_system=role_data["is_system"],
                created_by="system",
            )

            for perm_code in role_data["permissions"]:
                perm = await get_permission_by_code(db, perm_code)
                if perm:
                    await assign_permission_to_role(db, role.id, perm.id)

            logger.info("role_seeded", code=role_data["code"])


async def create_departments(db: AsyncSession) -> None:
    """创建部门"""
    departments = [
        {
            "name": "技术研发部",
            "code": "tech",
            "parent_id": None,
            "description": "负责技术研发工作",
            "sort_order": 1,
        },
        {
            "name": "产品管理部",
            "code": "product",
            "parent_id": None,
            "description": "负责产品管理工作",
            "sort_order": 2,
        },
        {
            "name": "后端开发组",
            "code": "backend",
            "parent_id": None,
            "description": "后端开发组",
            "sort_order": 10,
        },
    ]

    from app.services.organization_service import create_department

    for dept in departments:
        existing = await db.execute(select(Department).filter(Department.code == dept["code"]))
        if not existing.scalar_one_or_none():
            await create_department(
                db,
                create_data=None,
                current_user_id="system",
            )

            dept_obj = Department(
                id=f"dept_{uuid.uuid4().hex[:16]}",
                tenant_id="default",
                name=dept["name"],
                code=dept["code"],
                parent_id=dept["parent_id"],
                description=dept["description"],
                status="active",
                sort_order=dept["sort_order"],
                created_by="system",
            )
            db.add(dept_obj)
            await db.flush()
            logger.info("department_seeded", code=dept["code"])


async def create_user_groups(db: AsyncSession) -> None:
    """创建用户组"""
    groups = [
        {
            "name": "研发团队",
            "code": "rd_team",
            "description": "研发团队",
        },
        {
            "name": "产品团队",
            "code": "product_team",
            "description": "产品团队",
        },
    ]

    for group in groups:
        existing = await db.execute(select(UserGroup).filter(UserGroup.code == group["code"]))
        if not existing.scalar_one_or_none():
            group_obj = UserGroup(
                id=f"grp_{uuid.uuid4().hex[:16]}",
                tenant_id="default",
                name=group["name"],
                code=group["code"],
                description=group["description"],
                status="active",
                created_by="system",
            )
            db.add(group_obj)
            await db.flush()
            logger.info("user_group_seeded", code=group["code"])


async def create_users(db: AsyncSession) -> None:
    """创建用户"""
    users = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "系统管理员",
            "phone": "13800138000",
            "is_superuser": True,
            "is_active": True,
            "roles": ["super_admin"],
            "departments": [("tech", True)],
            "groups": ["rd_team"],
        },
        {
            "username": "kb_admin",
            "email": "kb_admin@example.com",
            "full_name": "知识库管理员",
            "phone": "13800138001",
            "is_superuser": False,
            "is_active": True,
            "roles": ["knowledge_base_admin"],
            "departments": [("tech", False)],
            "groups": ["rd_team"],
        },
        {
            "username": "user_a",
            "email": "user_a@example.com",
            "full_name": "用户A",
            "phone": "13800138002",
            "is_superuser": False,
            "is_active": True,
            "roles": ["normal_user"],
            "departments": [("tech", True)],
            "groups": ["rd_team"],
        },
        {
            "username": "user_b",
            "email": "user_b@example.com",
            "full_name": "用户B",
            "phone": "13800138003",
            "is_superuser": False,
            "is_active": True,
            "roles": ["normal_user"],
            "departments": [("product", True)],
            "groups": ["product_team"],
        },
        {
            "username": "disabled_user",
            "email": "disabled@example.com",
            "full_name": "禁用用户",
            "phone": "13800138004",
            "is_superuser": False,
            "is_active": False,
            "roles": ["normal_user"],
            "departments": [("tech", True)],
            "groups": [],
        },
    ]

    for user_data in users:
        existing = await db.execute(
            select(User).filter(
                and_(
                    (User.username == user_data["username"]) | (User.email == user_data["email"]),
                    User.deleted_at.is_(None),
                )
            )
        )
        if not existing.scalar_one_or_none():
            user = User(
                id=f"usr_{uuid.uuid4().hex[:16]}",
                tenant_id="default",
                username=user_data["username"],
                email=user_data["email"],
                password_hash=get_password_hash(DEFAULT_PASSWORD),
                full_name=user_data["full_name"],
                phone=user_data["phone"],
                is_superuser=user_data["is_superuser"],
                is_active=user_data["is_active"],
                created_by="system",
            )
            db.add(user)
            await db.flush()
            logger.info("user_seeded", username=user_data["username"])


async def assign_user_roles(db: AsyncSession) -> None:
    """分配用户角色"""
    user_role_mapping = {
        "admin": ["super_admin"],
        "kb_admin": ["knowledge_base_admin"],
        "user_a": ["normal_user"],
        "user_b": ["normal_user"],
        "disabled_user": ["normal_user"],
    }

    for username, role_codes in user_role_mapping.items():
        user_result = await db.execute(select(User).filter(User.username == username))
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        for role_code in role_codes:
            role_result = await db.execute(select(Role).filter(Role.code == role_code))
            role = role_result.scalar_one_or_none()
            if role:
                try:
                    await assign_role_to_user(db, user.id, role.id)
                except Exception:
                    pass


async def assign_user_organizations(db: AsyncSession) -> None:
    """分配用户到部门和用户组"""
    user_dept_mapping = {
        "admin": [("tech", True)],
        "kb_admin": [("tech", False)],
        "user_a": [("tech", True)],
        "user_b": [("product", True)],
        "disabled_user": [("tech", True)],
    }

    user_group_mapping = {
        "admin": ["rd_team"],
        "kb_admin": ["rd_team"],
        "user_a": ["rd_team"],
        "user_b": ["product_team"],
    }

    for username, depts in user_dept_mapping.items():
        user_result = await db.execute(select(User).filter(User.username == username))
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        for dept_code, is_primary in depts:
            dept_result = await db.execute(select(Department).filter(Department.code == dept_code))
            dept = dept_result.scalar_one_or_none()
            if dept:
                try:
                    await assign_user_to_department(db, user.id, dept.id, is_primary)
                except Exception:
                    pass

    for username, groups in user_group_mapping.items():
        user_result = await db.execute(select(User).filter(User.username == username))
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        for group_code in groups:
            group_result = await db.execute(select(UserGroup).filter(UserGroup.code == group_code))
            group = group_result.scalar_one_or_none()
            if group:
                try:
                    await add_user_to_group(db, user.id, group.id)
                except Exception:
                    pass