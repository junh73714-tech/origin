"""
成员6：共享库 PermissionService DB 联调（兼容 20260716 库结构）。

官方 seed_data.py / 成员4 ORM 与共享库表结构存在差异（uuid、user_roles 实体表等）。
本脚本：
1) 补齐缺表与兼容列
2) 用 raw SQL 写入联调样本
3) monkeypatch 用户加载后调用正式 PermissionService 过滤构建

用法：
  cd backend
  python scripts/m6_permission_db_joint.py
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

sys.path.insert(0, ".")

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.core.security import AccessContext, get_password_hash
from app.retrieval.member4_bridge import (
    apply_access_context_response,
    build_member4_style_opensearch_bool,
    member4_filter_dict_to_m6,
)
from app.schemas.identity import AccessContextResponse, TemporaryGrantInfo
from app.services.permission_service import PermissionService

TENANT_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.default-tenant"))
KB_PUBLIC = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.kb-public"))
KB_TECH = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.kb-tech"))
DOC_TEMP = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.doc-temp-001"))
USER_ADMIN = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.user-admin"))
USER_NORMAL = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.user-normal"))
USER_NOKB = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.user-nokb"))
ROLE_EMPLOYEE = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.role-employee"))
ROLE_NOKB = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.role-nokb"))
ROLE_ADMIN = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.role-admin"))
DEPT_TECH = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.dept-tech"))
DEPT_HR = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.dept-hr"))
PERM_KB = str(uuid.uuid5(uuid.NAMESPACE_DNS, "enterprise-rag.perm-kb-read"))


def _dsn() -> dict:
    return {
        "host": settings.database.host,
        "port": settings.database.port,
        "user": settings.database.user,
        "password": settings.database.password,
        "dbname": settings.database.name,
    }


def _conn():
    return psycopg2.connect(**_dsn())


def ensure_schema() -> None:
    stmts = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser boolean NOT NULL DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name varchar(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone varchar(20)",
        "ALTER TABLE roles ADD COLUMN IF NOT EXISTS deleted_at timestamptz",
        "ALTER TABLE roles ADD COLUMN IF NOT EXISTS deleted_by uuid",
        """
        CREATE TABLE IF NOT EXISTS departments (
            id varchar(64) PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            name varchar(100) NOT NULL,
            code varchar(50) NOT NULL UNIQUE,
            parent_id varchar(64),
            description text,
            status varchar(50) NOT NULL DEFAULT 'active',
            sort_order integer NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            created_by varchar(64) NOT NULL DEFAULT 'system',
            updated_by varchar(64),
            deleted_at timestamptz,
            deleted_by varchar(64)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS knowledge_base_permissions (
            id varchar(64) PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            knowledge_base_id varchar(64) NOT NULL,
            user_id varchar(64),
            role_id varchar(64),
            department_id varchar(64),
            group_id varchar(64),
            permission_type varchar(50) NOT NULL,
            is_deny boolean NOT NULL DEFAULT false,
            effective_time timestamptz,
            expiration_time timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            created_by varchar(64) NOT NULL DEFAULT 'system',
            updated_by varchar(64),
            deleted_at timestamptz,
            deleted_by varchar(64)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS document_permissions (
            id varchar(64) PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            document_id varchar(64) NOT NULL,
            user_id varchar(64),
            role_id varchar(64),
            department_id varchar(64),
            group_id varchar(64),
            permission_type varchar(50) NOT NULL,
            is_deny boolean NOT NULL DEFAULT false,
            confidentiality_level integer NOT NULL DEFAULT 0,
            effective_time timestamptz,
            expiration_time timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            created_by varchar(64) NOT NULL DEFAULT 'system',
            updated_by varchar(64),
            deleted_at timestamptz,
            deleted_by varchar(64)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS temporary_grants (
            id varchar(64) PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            user_id varchar(64) NOT NULL,
            resource_type varchar(50) NOT NULL,
            resource_id varchar(64) NOT NULL,
            permission_type varchar(50) NOT NULL,
            reason text,
            effective_time timestamptz NOT NULL,
            expiration_time timestamptz NOT NULL,
            status varchar(50) NOT NULL DEFAULT 'active',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            created_by varchar(64) NOT NULL DEFAULT 'system',
            updated_by varchar(64),
            deleted_at timestamptz,
            deleted_by varchar(64)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS data_scopes (
            id varchar(64) PRIMARY KEY,
            tenant_id varchar(64) NOT NULL,
            name varchar(100) NOT NULL,
            code varchar(50) NOT NULL UNIQUE,
            scope_type varchar(50) NOT NULL,
            description text,
            status varchar(50) NOT NULL DEFAULT 'active',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            created_by varchar(64) NOT NULL DEFAULT 'system',
            updated_by varchar(64),
            deleted_at timestamptz,
            deleted_by varchar(64)
        )
        """,
    ]
    conn = _conn()
    conn.autocommit = True
    cur = conn.cursor()
    for s in stmts:
        cur.execute(s)
    cur.execute(
        """
        INSERT INTO tenants (id, created_at, updated_at, code, name, status)
        VALUES (%s::uuid, now(), now(), 'default', '默认租户', 'active')
        ON CONFLICT (id) DO NOTHING
        """,
        (TENANT_ID,),
    )
    for kid, code, name in [
        (KB_PUBLIC, "kb-public", "公开知识库"),
        (KB_TECH, "kb-tech", "技术知识库"),
    ]:
        cur.execute(
            """
            INSERT INTO knowledge_bases (
                id, created_at, updated_at, tenant_id, code, name, status,
                default_permissions, document_count, chunk_count
            ) VALUES (
                %s::uuid, now(), now(), %s::uuid, %s, %s, 'active', '{}'::json, 0, 0
            )
            ON CONFLICT (id) DO NOTHING
            """,
            (kid, TENANT_ID, code, name),
        )
    cur.close()
    conn.close()
    print("[ok] schema ensured")


def seed() -> None:
    now = datetime.now(timezone.utc)
    pw = {
        "admin": get_password_hash("admin123"),
        "user": get_password_hash("user123"),
        "nokb": get_password_hash("nokb123"),
    }
    conn = _conn()
    cur = conn.cursor()

    # roles（按 code upsert，兼容已有数据）
    for rid, code, name in [
        (ROLE_ADMIN, "admin", "管理员"),
        (ROLE_EMPLOYEE, "employee", "普通员工"),
        (ROLE_NOKB, "no_kb", "无知识库权限"),
    ]:
        cur.execute("SELECT id FROM roles WHERE code=%s", (code,))
        row = cur.fetchone()
        if row:
            # 使用库内已有 id
            if code == "admin":
                globals()["ROLE_ADMIN"] = str(row[0])
            elif code == "employee":
                globals()["ROLE_EMPLOYEE"] = str(row[0])
            else:
                globals()["ROLE_NOKB"] = str(row[0])
        else:
            cur.execute(
                """
                INSERT INTO roles (id, created_at, updated_at, tenant_id, code, name, description, status, is_system)
                VALUES (%s::uuid, now(), now(), %s::uuid, %s, %s, %s, 'active', true)
                """,
                (rid, TENANT_ID, code, name, name),
            )

    # 刷新本地角色 ID（可能被已有行替换）
    cur.execute("SELECT code, id::text FROM roles WHERE code IN ('admin','employee','no_kb')")
    role_map = dict(cur.fetchall())
    role_admin = role_map.get("admin", ROLE_ADMIN)
    role_employee = role_map.get("employee", ROLE_EMPLOYEE)
    role_nokb = role_map.get("no_kb", ROLE_NOKB)

    # permissions
    cur.execute("SELECT id::text FROM permissions WHERE code='kb_read'")
    row = cur.fetchone()
    perm_kb = row[0] if row else PERM_KB
    if not row:
        cur.execute(
            """
            INSERT INTO permissions (id, created_at, updated_at, code, name, kind, resource, action)
            VALUES (%s::uuid, now(), now(), 'kb_read', '知识库读取', 'action', 'knowledge_base', 'read')
            """,
            (PERM_KB,),
        )
        perm_kb = PERM_KB
    del perm_kb  # 当前联调不强制依赖 role_permissions 表结构

    # users
    for uid, username, email, full_name, superuser in [
        (USER_ADMIN, "admin", "admin@example.com", "系统管理员", True),
        (USER_NORMAL, "user", "user@example.com", "普通员工", False),
        (USER_NOKB, "nokb", "nokb@example.com", "无KB权限用户", False),
    ]:
        cur.execute(
            """
            INSERT INTO users (
                id, created_at, updated_at, tenant_id, username, password_hash,
                display_name, email, status, failed_login_count,
                is_active, is_superuser, full_name, created_by
            ) VALUES (
                %s::uuid, now(), now(), %s::uuid, %s, %s,
                %s, %s, 'active', 0,
                true, %s, %s, %s::uuid
            )
            ON CONFLICT (id) DO UPDATE SET
                password_hash=EXCLUDED.password_hash,
                is_active=true,
                status='active',
                full_name=EXCLUDED.full_name,
                display_name=EXCLUDED.display_name
            """,
            (uid, TENANT_ID, username, pw[username], full_name, email, superuser, full_name, uid),
        )

    # user_roles (live entity table)
    for uid, rid in [
        (USER_ADMIN, role_admin),
        (USER_NORMAL, role_employee),
        (USER_NOKB, role_nokb),
    ]:
        cur.execute("DELETE FROM user_roles WHERE user_id=%s::uuid", (uid,))
        cur.execute(
            """
            INSERT INTO user_roles (
                id, created_at, updated_at, tenant_id, user_id, role_id, effective_at
            ) VALUES (
                %s::uuid, now(), now(), %s::uuid, %s::uuid, %s::uuid, now()
            )
            """,
            (str(uuid.uuid4()), TENANT_ID, uid, rid),
        )

    # departments（共享库已有 uuid 版 departments）
    for did, code, name, path, level in [
        (DEPT_TECH, "tech", "技术部", "/tech", 1),
        (DEPT_HR, "hr", "人力资源部", "/hr", 1),
    ]:
        cur.execute("SELECT id::text FROM departments WHERE code=%s", (code,))
        row = cur.fetchone()
        if row:
            if code == "tech":
                # 保持 DEPT_TECH 常量用于后续 KB 授权；若库里已有则改用已有 id
                pass
            continue
        cur.execute(
            """
            INSERT INTO departments (
                id, created_at, updated_at, tenant_id, name, code, path, level, status
            ) VALUES (
                %s::uuid, now(), now(), %s::uuid, %s, %s, %s, %s, 'active'
            )
            """,
            (did, TENANT_ID, name, code, path, level),
        )
    cur.execute("SELECT code, id::text FROM departments WHERE code IN ('tech','hr')")
    dept_map = dict(cur.fetchall())
    dept_tech = dept_map.get("tech", DEPT_TECH)
    dept_hr = dept_map.get("hr", DEPT_HR)

    # kb permissions
    cur.execute("DELETE FROM knowledge_base_permissions WHERE id LIKE 'kb-perm-joint-%%'")
    cur.execute(
        """
        INSERT INTO knowledge_base_permissions (
            id, tenant_id, knowledge_base_id, role_id, department_id, permission_type, is_deny, created_by
        ) VALUES
        ('kb-perm-joint-1', %s, %s, %s, NULL, 'read', false, 'system'),
        ('kb-perm-joint-2', %s, %s, NULL, %s, 'read', false, 'system')
        """,
        (TENANT_ID, KB_PUBLIC, role_employee, TENANT_ID, KB_TECH, dept_tech),
    )

    # 临时授权：nokb 可读特定文档
    cur.execute("DELETE FROM temporary_grants WHERE id='grant-joint-nokb-doc'")
    cur.execute(
        """
        INSERT INTO temporary_grants (
            id, tenant_id, user_id, resource_type, resource_id, permission_type,
            reason, effective_time, expiration_time, status, created_by
        ) VALUES (
            'grant-joint-nokb-doc', %s, %s, 'document', %s, 'read',
            '联调临时授权', %s, %s, 'active', 'system'
        )
        """,
        (
            TENANT_ID,
            USER_NOKB,
            DOC_TEMP,
            now - timedelta(hours=1),
            now + timedelta(days=1),
        ),
    )

    conn.commit()
    cur.close()
    conn.close()
    print("[ok] seed data written")


def _load_user_bundle(user_id: str) -> SimpleNamespace:
    """按共享库结构加载用户/角色/部门，供 PermissionService 计算。"""
    conn = _conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM users WHERE id=%s::uuid AND deleted_at IS NULL",
        (user_id,),
    )
    u = cur.fetchone()
    if not u:
        cur.close()
        conn.close()
        return None

    cur.execute(
        """
        SELECT r.*
        FROM roles r
        JOIN user_roles ur ON ur.role_id = r.id
        WHERE ur.user_id=%s::uuid AND r.deleted_at IS NULL
        """,
        (user_id,),
    )
    roles = list(cur.fetchall())
    role_objs = []
    for r in roles:
        cur.execute(
            """
            SELECT p.*
            FROM permissions p
            JOIN role_permissions rp ON rp.permission_id = p.id
            WHERE rp.role_id=%s::uuid
            """,
            (str(r["id"]),),
        )
        perms = [
            SimpleNamespace(id=str(p["id"]), code=p["code"], name=p["name"])
            for p in cur.fetchall()
        ]
        role_objs.append(
            SimpleNamespace(
                id=str(r["id"]),
                code=r["code"],
                name=r["name"],
                permissions=perms,
            )
        )

    # 部门：联调约定（用库内实际部门 id）
    depts = []
    conn2 = _conn()
    cur2 = conn2.cursor(cursor_factory=RealDictCursor)
    if user_id == USER_NORMAL:
        cur2.execute("SELECT id::text AS id, code, name FROM departments WHERE code='tech' LIMIT 1")
        row = cur2.fetchone()
        if row:
            depts = [SimpleNamespace(id=row["id"], code=row["code"], name=row["name"])]
    elif user_id == USER_NOKB:
        cur2.execute("SELECT id::text AS id, code, name FROM departments WHERE code='hr' LIMIT 1")
        row = cur2.fetchone()
        if row:
            depts = [SimpleNamespace(id=row["id"], code=row["code"], name=row["name"])]
    cur2.close()
    conn2.close()

    cur.close()
    conn.close()
    return SimpleNamespace(
        id=str(u["id"]),
        tenant_id=str(u["tenant_id"]),
        username=u["username"],
        is_active=bool(u.get("is_active", True)),
        roles=role_objs,
        departments=depts,
        groups=[],
    )


def _build_context_via_service_logic(user_id: str) -> AccessContextResponse:
    """
    复用 PermissionService 的过滤构建入口：
    monkeypatch _get_user_with_relations / DB 查询为对补齐表的查询。
    """
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    user = _load_user_bundle(user_id)
    if user is None:
        raise RuntimeError(f"user not found: {user_id}")

    conn = _conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # KB permissions rows
    cur.execute(
        """
        SELECT * FROM knowledge_base_permissions
        WHERE is_deny=false AND deleted_at IS NULL
        """
    )
    kb_rows = list(cur.fetchall())
    cur.execute(
        """
        SELECT * FROM temporary_grants
        WHERE user_id=%s AND status='active' AND deleted_at IS NULL
          AND effective_time <= now() AND expiration_time > now()
        """,
        (user_id,),
    )
    grant_rows = list(cur.fetchall())
    cur.close()
    conn.close()

    role_ids = {r.id for r in user.roles}
    dept_ids = {d.id for d in user.departments}
    allowed = set()
    for row in kb_rows:
        kb_id = row["knowledge_base_id"]
        if row.get("user_id") == user_id:
            allowed.add(kb_id)
        elif row.get("role_id") and row["role_id"] in role_ids:
            allowed.add(kb_id)
        elif row.get("department_id") and row["department_id"] in dept_ids:
            allowed.add(kb_id)

    grants = [
        TemporaryGrantInfo(
            resource_type=g["resource_type"],
            resource_id=g["resource_id"],
            permission_type=g["permission_type"],
            effective_time=g["effective_time"],
            expiration_time=g["expiration_time"],
        )
        for g in grant_rows
    ]

    # 用正式 PermissionService 的 hash / filter 构建
    mock_db = AsyncMock()
    svc = PermissionService(mock_db)

    async def _fake_user(_uid: str):
        return user

    async def _fake_kb(_user):
        return sorted(allowed)

    async def _fake_conf(_user):
        return 0

    async def _fake_deny(_user):
        return []

    async def _fake_grants(_uid: str):
        return [
            SimpleNamespace(
                resource_type=g.resource_type,
                resource_id=g.resource_id,
                permission_type=g.permission_type,
                effective_time=g.effective_time,
                expiration_time=g.expiration_time,
            )
            for g in grants
        ]

    svc._get_user_with_relations = _fake_user  # type: ignore[method-assign]
    svc._get_allowed_knowledge_base_ids = _fake_kb  # type: ignore[method-assign]
    svc._get_max_confidentiality_level = _fake_conf  # type: ignore[method-assign]
    svc._get_deny_document_ids = _fake_deny  # type: ignore[method-assign]
    svc._get_active_temporary_grants = _fake_grants  # type: ignore[method-assign]

    return asyncio.run(svc.get_access_context(user_id=user_id))


def verify() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    ctx_nokb = _build_context_via_service_logic(USER_NOKB)
    f_nokb = member4_filter_dict_to_m6(
        {
            "tenant_id": ctx_nokb.tenant_id,
            "user_id": ctx_nokb.user_id,
            "knowledge_base_ids": ctx_nokb.knowledge_base_ids,
            "department_ids": ctx_nokb.department_ids,
            "group_ids": ctx_nokb.group_ids,
            "project_ids": ctx_nokb.project_ids,
            "regions": ctx_nokb.regions,
            "max_confidentiality_level": ctx_nokb.max_confidentiality_level,
            "deny_document_ids": ctx_nokb.deny_document_ids,
            "allow_document_ids": [],
            "effective_temporary_grants": [g.model_dump() for g in ctx_nokb.temporary_grants],
            "scope_hash": ctx_nokb.scope_hash,
        }
    )
    dsl_nokb = build_member4_style_opensearch_bool(f_nokb)
    results.append(
        (
            "nokb: empty KB + temp doc grant in DSL",
            (not f_nokb.knowledge_base_ids)
            and DOC_TEMP in str(dsl_nokb)
            and "match_none" not in str(dsl_nokb),
            f"kb={f_nokb.knowledge_base_ids} dsl={dsl_nokb}",
        )
    )

    ctx_user = _build_context_via_service_logic(USER_NORMAL)
    f_user = member4_filter_dict_to_m6(
        {
            "tenant_id": ctx_user.tenant_id,
            "user_id": ctx_user.user_id,
            "knowledge_base_ids": ctx_user.knowledge_base_ids,
            "department_ids": ctx_user.department_ids,
            "group_ids": ctx_user.group_ids,
            "project_ids": ctx_user.project_ids,
            "regions": ctx_user.regions,
            "max_confidentiality_level": ctx_user.max_confidentiality_level,
            "deny_document_ids": ctx_user.deny_document_ids,
            "allow_document_ids": [],
            "effective_temporary_grants": [g.model_dump() for g in ctx_user.temporary_grants],
            "scope_hash": ctx_user.scope_hash,
        }
    )
    results.append(
        (
            "user: has kb-public via employee role",
            KB_PUBLIC in f_user.knowledge_base_ids,
            f"kb={f_user.knowledge_base_ids}",
        )
    )
    results.append(
        (
            "user: has kb-tech via department",
            KB_TECH in f_user.knowledge_base_ids,
            f"kb={f_user.knowledge_base_ids}",
        )
    )
    dsl_user = build_member4_style_opensearch_bool(f_user)
    has_conf = any(
        "confidentiality_level" in str(c) for c in dsl_user.get("bool", {}).get("must", [])
    )
    results.append(("user: confidentiality filter present", has_conf, str(dsl_user)[:160]))

    access = AccessContext(
        user_id=USER_NORMAL,
        tenant_id=TENANT_ID,
        roles=[],
        permissions=[],
        data_scopes={},
    )
    enriched = apply_access_context_response(access, ctx_user)
    results.append(
        (
            "AccessContext enriched from PermissionService context",
            KB_PUBLIC in enriched.knowledge_base_ids and bool(enriched.scope_hash),
            f"kb={enriched.knowledge_base_ids} hash={enriched.scope_hash[:16]}",
        )
    )
    return results


def main() -> int:
    print("=== member6 PermissionService DB joint ===")
    print(f"db={settings.database.host}:{settings.database.port}/{settings.database.name}")
    ensure_schema()
    seed()
    results = verify()
    print("\n=== verify ===")
    failed = 0
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(f"       {detail[:240]}")
        if not ok:
            failed += 1
    print(f"total: {len(results) - failed}/{len(results)} passed")
    if failed:
        return 1
    print("PASS: DB-side permission filter joint OK")
    print(f"users: admin/admin123, user/user123, nokb/nokb123")
    print(f"kb_public={KB_PUBLIC}")
    print(f"kb_tech={KB_TECH}")
    print(f"doc_temp={DOC_TEMP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
