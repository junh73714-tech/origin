"""
成员4：身份认证与权限系统种子数据脚本

生成测试用户、角色、权限、部门、知识库权限和临时授权样本数据。

使用方式：
    python -m scripts.seed_data
    或
    在启动时通过 API 调用：POST /api/v1/seed
"""
import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.insert(0, ".")

from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.auth import Permission, Role, user_roles, role_permissions
from app.models.identity import (
    Department,
    UserGroup,
    KnowledgeBasePermission,
    TemporaryGrant,
    user_departments,
    user_group_members,
)
from app.models.user import User


TENANT_ID = "default-tenant"


async def create_users(db) -> Dict[str, User]:
    """创建测试用户"""
    users = {}

    admin_user = User(
        id="user-admin-001",
        tenant_id=TENANT_ID,
        email="admin@example.com",
        username="admin",
        password_hash=get_password_hash("admin123"),
        full_name="系统管理员",
        phone="13800138000",
        is_active=True,
        is_superuser=True,
        status="active",
    )

    normal_user = User(
        id="user-normal-001",
        tenant_id=TENANT_ID,
        email="user@example.com",
        username="user",
        password_hash=get_password_hash("user123"),
        full_name="普通员工",
        phone="13800138001",
        is_active=True,
        is_superuser=False,
        status="active",
    )

    no_kb_user = User(
        id="user-nokb-001",
        tenant_id=TENANT_ID,
        email="nokb@example.com",
        username="nokb",
        password_hash=get_password_hash("nokb123"),
        full_name="无KB权限用户",
        phone="13800138002",
        is_active=True,
        is_superuser=False,
        status="active",
    )

    locked_user = User(
        id="user-locked-001",
        tenant_id=TENANT_ID,
        email="locked@example.com",
        username="locked",
        password_hash=get_password_hash("locked123"),
        full_name="被锁定用户",
        phone="13800138003",
        is_active=False,
        is_superuser=False,
        status="locked",
    )

    db.add_all([admin_user, normal_user, no_kb_user, locked_user])
    await db.flush()

    users["admin"] = admin_user
    users["user"] = normal_user
    users["nokb"] = no_kb_user
    users["locked"] = locked_user

    print(f"  创建测试用户: {len(users)} 个")
    return users


async def create_roles(db) -> Dict[str, Role]:
    """创建系统角色"""
    roles = {}

    super_admin_role = Role(
        id="role-super-admin",
        tenant_id=TENANT_ID,
        name="超级管理员",
        code="super_admin",
        description="拥有系统所有权限",
        is_system=True,
    )

    admin_role = Role(
        id="role-admin",
        tenant_id=TENANT_ID,
        name="管理员",
        code="admin",
        description="管理部门和用户",
        is_system=True,
    )

    employee_role = Role(
        id="role-employee",
        tenant_id=TENANT_ID,
        name="普通员工",
        code="employee",
        description="基础访问权限",
        is_system=True,
    )

    no_kb_role = Role(
        id="role-no-kb",
        tenant_id=TENANT_ID,
        name="无知识库权限",
        code="no_kb",
        description="无法访问任何知识库",
        is_system=False,
    )

    db.add_all([super_admin_role, admin_role, employee_role, no_kb_role])
    await db.flush()

    roles["super_admin"] = super_admin_role
    roles["admin"] = admin_role
    roles["employee"] = employee_role
    roles["no_kb"] = no_kb_role

    print(f"  创建角色: {len(roles)} 个")
    return roles


async def create_permissions(db) -> Dict[str, Permission]:
    """创建系统权限"""
    permissions = {}

    perms = [
        ("document_read", "文档读取", "document", "read"),
        ("document_write", "文档写入", "document", "write"),
        ("document_delete", "文档删除", "document", "delete"),
        ("kb_read", "知识库读取", "knowledge_base", "read"),
        ("kb_write", "知识库写入", "knowledge_base", "write"),
        ("kb_delete", "知识库删除", "knowledge_base", "delete"),
        ("qa_read", "问答读取", "qa", "read"),
        ("qa_write", "问答写入", "qa", "write"),
        ("user_read", "用户读取", "user", "read"),
        ("user_write", "用户写入", "user", "write"),
        ("role_read", "角色读取", "role", "read"),
        ("role_write", "角色写入", "role", "write"),
        ("department_read", "部门读取", "department", "read"),
        ("department_write", "部门写入", "department", "write"),
    ]

    for code, name, resource_type, action in perms:
        perm = Permission(
            id=f"perm-{code}",
            tenant_id=TENANT_ID,
            name=name,
            code=code,
            resource_type=resource_type,
            action=action,
        )
        db.add(perm)
        permissions[code] = perm

    await db.flush()
    print(f"  创建权限: {len(permissions)} 个")
    return permissions


async def assign_user_roles(db, users: Dict[str, User], roles: Dict[str, Role]):
    """分配用户角色"""
    assignments = [
        (users["admin"].id, roles["super_admin"].id),
        (users["user"].id, roles["employee"].id),
        (users["nokb"].id, roles["no_kb"].id),
    ]

    for user_id, role_id in assignments:
        await db.execute(
            user_roles.insert().values(user_id=user_id, role_id=role_id)
        )

    print(f"  分配用户角色: {len(assignments)} 组")


async def assign_role_permissions(db, roles: Dict[str, Role], permissions: Dict[str, Permission]):
    """分配角色权限"""
    super_admin_perms = list(permissions.keys())
    admin_perms = [
        "document_read", "document_write",
        "kb_read", "kb_write",
        "qa_read", "qa_write",
        "user_read", "user_write",
        "role_read",
        "department_read", "department_write",
    ]
    employee_perms = [
        "document_read",
        "kb_read",
        "qa_read",
    ]

    role_perm_map = {
        "super_admin": super_admin_perms,
        "admin": admin_perms,
        "employee": employee_perms,
    }

    for role_code, perm_codes in role_perm_map.items():
        role = roles[role_code]
        for perm_code in perm_codes:
            perm = permissions[perm_code]
            await db.execute(
                role_permissions.insert().values(role_id=role.id, permission_id=perm.id)
            )

    print(f"  分配角色权限: {sum(len(v) for v in role_perm_map.values())} 组")


async def create_departments(db) -> Dict[str, Department]:
    """创建部门"""
    departments = {}

    root_dept = Department(
        id="dept-root",
        tenant_id=TENANT_ID,
        name="公司总部",
        code="root",
        parent_id=None,
        description="公司总部",
        status="active",
        sort_order=0,
    )

    tech_dept = Department(
        id="dept-tech",
        tenant_id=TENANT_ID,
        name="技术部",
        code="tech",
        parent_id="dept-root",
        description="技术研发部门",
        status="active",
        sort_order=1,
    )

    hr_dept = Department(
        id="dept-hr",
        tenant_id=TENANT_ID,
        name="人力资源部",
        code="hr",
        parent_id="dept-root",
        description="人力资源管理部门",
        status="active",
        sort_order=2,
    )

    db.add_all([root_dept, tech_dept, hr_dept])
    await db.flush()

    departments["root"] = root_dept
    departments["tech"] = tech_dept
    departments["hr"] = hr_dept

    print(f"  创建部门: {len(departments)} 个")
    return departments


async def create_user_groups(db) -> Dict[str, UserGroup]:
    """创建用户组"""
    groups = {}

    tech_group = UserGroup(
        id="group-tech",
        tenant_id=TENANT_ID,
        name="技术团队",
        code="tech_team",
        description="技术部员工组",
        status="active",
    )

    admin_group = UserGroup(
        id="group-admin",
        tenant_id=TENANT_ID,
        name="管理员组",
        code="admin_group",
        description="系统管理员组",
        status="active",
    )

    db.add_all([tech_group, admin_group])
    await db.flush()

    groups["tech"] = tech_group
    groups["admin"] = admin_group

    print(f"  创建用户组: {len(groups)} 个")
    return groups


async def assign_user_departments(db, users: Dict[str, User], departments: Dict[str, Department]):
    """分配用户部门"""
    assignments = [
        (users["admin"].id, departments["root"].id, True),
        (users["user"].id, departments["tech"].id, True),
        (users["nokb"].id, departments["hr"].id, True),
    ]

    for user_id, dept_id, is_primary in assignments:
        await db.execute(
            user_departments.insert().values(
                user_id=user_id, department_id=dept_id, is_primary=is_primary
            )
        )

    print(f"  分配用户部门: {len(assignments)} 组")


async def assign_user_groups(db, users: Dict[str, User], groups: Dict[str, UserGroup]):
    """分配用户组"""
    assignments = [
        (users["admin"].id, groups["admin"].id),
        (users["user"].id, groups["tech"].id),
    ]

    for user_id, group_id in assignments:
        await db.execute(
            user_group_members.insert().values(user_id=user_id, group_id=group_id)
        )

    print(f"  分配用户组: {len(assignments)} 组")


async def create_kb_permissions(db, users: Dict[str, User], roles: Dict[str, Role], departments: Dict[str, Department]):
    """创建知识库权限样本"""
    kb_perms = [
        KnowledgeBasePermission(
            id="kb-perm-001",
            tenant_id=TENANT_ID,
            knowledge_base_id="kb-public",
            user_id=None,
            role_id=roles["employee"].id,
            department_id=None,
            group_id=None,
            permission_type="read",
            is_deny=False,
        ),
        KnowledgeBasePermission(
            id="kb-perm-002",
            tenant_id=TENANT_ID,
            knowledge_base_id="kb-tech",
            user_id=None,
            role_id=None,
            department_id=departments["tech"].id,
            group_id=None,
            permission_type="read",
            is_deny=False,
        ),
        KnowledgeBasePermission(
            id="kb-perm-003",
            tenant_id=TENANT_ID,
            knowledge_base_id="kb-tech",
            user_id=users["admin"].id,
            role_id=None,
            department_id=None,
            group_id=None,
            permission_type="write",
            is_deny=False,
        ),
        KnowledgeBasePermission(
            id="kb-perm-004",
            tenant_id=TENANT_ID,
            knowledge_base_id="kb-confidential",
            user_id=None,
            role_id=roles["super_admin"].id,
            department_id=None,
            group_id=None,
            permission_type="read",
            is_deny=False,
        ),
        KnowledgeBasePermission(
            id="kb-perm-005",
            tenant_id=TENANT_ID,
            knowledge_base_id="kb-all",
            user_id=users["user"].id,
            role_id=None,
            department_id=None,
            group_id=None,
            permission_type="read",
            is_deny=False,
        ),
    ]

    db.add_all(kb_perms)
    await db.flush()

    print(f"  创建知识库权限: {len(kb_perms)} 条")


async def create_temporary_grants(db, users: Dict[str, User]):
    """创建临时授权样本"""
    now = datetime.now()

    grants = [
        TemporaryGrant(
            id="grant-001",
            tenant_id=TENANT_ID,
            user_id=users["user"].id,
            resource_type="knowledge_base",
            resource_id="kb-temp",
            permission_type="read",
            reason="临时访问项目文档",
            effective_time=now - timedelta(hours=1),
            expiration_time=now + timedelta(days=7),
            status="active",
        ),
        TemporaryGrant(
            id="grant-002",
            tenant_id=TENANT_ID,
            user_id=users["nokb"].id,
            resource_type="document",
            resource_id="doc-temp-001",
            permission_type="read",
            reason="查看特定文档",
            effective_time=now - timedelta(hours=2),
            expiration_time=now + timedelta(days=1),
            status="active",
        ),
        TemporaryGrant(
            id="grant-003",
            tenant_id=TENANT_ID,
            user_id=users["user"].id,
            resource_type="knowledge_base",
            resource_id="kb-expired",
            permission_type="read",
            reason="已过期授权",
            effective_time=now - timedelta(days=30),
            expiration_time=now - timedelta(days=1),
            status="expired",
        ),
    ]

    db.add_all(grants)
    await db.flush()

    print(f"  创建临时授权: {len(grants)} 条")


async def create_data_scopes(db):
    """创建数据范围"""
    scopes = [
        {"id": "scope-all", "name": "全部数据", "code": "all", "scope_type": "all"},
        {"id": "scope-self", "name": "仅自己", "code": "self", "scope_type": "self"},
        {"id": "scope-department", "name": "本部门", "code": "department", "scope_type": "department"},
        {"id": "scope-subtree", "name": "部门及下级", "code": "subtree", "scope_type": "subtree"},
    ]

    for scope in scopes:
        db.add(
            DataScope(
                id=scope["id"],
                tenant_id=TENANT_ID,
                name=scope["name"],
                code=scope["code"],
                scope_type=scope["scope_type"],
                status="active",
            )
        )

    await db.flush()
    print(f"  创建数据范围: {len(scopes)} 个")


async def main():
    """主函数"""
    print("=" * 60)
    print("成员4：身份认证与权限系统种子数据")
    print("=" * 60)

    async with async_session() as db:
        async with db.begin():
            print("\n1. 创建测试用户...")
            users = await create_users(db)

            print("\n2. 创建系统角色...")
            roles = await create_roles(db)

            print("\n3. 创建系统权限...")
            permissions = await create_permissions(db)

            print("\n4. 分配用户角色...")
            await assign_user_roles(db, users, roles)

            print("\n5. 分配角色权限...")
            await assign_role_permissions(db, roles, permissions)

            print("\n6. 创建部门...")
            departments = await create_departments(db)

            print("\n7. 创建用户组...")
            groups = await create_user_groups(db)

            print("\n8. 分配用户部门...")
            await assign_user_departments(db, users, departments)

            print("\n9. 分配用户组...")
            await assign_user_groups(db, users, groups)

            print("\n10. 创建知识库权限...")
            await create_kb_permissions(db, users, roles, departments)

            print("\n11. 创建临时授权...")
            await create_temporary_grants(db, users)

            print("\n12. 创建数据范围...")
            await create_data_scopes(db)

        await db.commit()

    print("\n" + "=" * 60)
    print("种子数据生成完成！")
    print("=" * 60)
    print("\n测试用户：")
    print("  - admin / admin123 (超级管理员)")
    print("  - user / user123 (普通员工，有KB权限)")
    print("  - nokb / nokb123 (无KB权限用户)")
    print("  - locked / locked123 (被锁定用户)")
    print("\n知识库权限：")
    print("  - kb-public: employee角色可读")
    print("  - kb-tech: 技术部可读")
    print("  - kb-confidential: 超级管理员可读")
    print("  - kb-all: user用户可读")
    print("\n临时授权：")
    print("  - user: kb-temp 7天有效")
    print("  - nokb: doc-temp-001 1天有效")
    print("  - user: kb-expired 已过期")


if __name__ == "__main__":
    asyncio.run(main())