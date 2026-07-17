"""
安全工具模块
提供密码哈希、JWT 令牌、访问上下文等安全功能
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 密码加密上下文 - 支持 bcrypt（旧密码）和 argon2（新密码）
# 新密码使用 argon2 哈希，旧 bcrypt 密码可自动验证
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    deprecated="auto",
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.secret_key,
        algorithm=settings.security.algorithm,
    )
    return encoded_jwt


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.security.refresh_token_expire_days
        )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.secret_key,
        algorithm=settings.security.algorithm,
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """解码令牌"""
    try:
        payload = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.algorithm],
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    """验证令牌并返回 payload"""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != token_type:
        return None
    return payload


class AccessContext:
    """
    访问上下文
    包含当前请求的用户信息和权限范围。
    扩展字段（scope_hash 等）兼容成员4/6契约，需成员1/4确认。
    """

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        roles: list[str],
        permissions: list[str],
        data_scopes: dict[str, list[str]] | None = None,
        role_ids: list[str] | None = None,
        department_ids: list[str] | None = None,
        group_ids: list[str] | None = None,
        knowledge_base_ids: list[str] | None = None,
        project_ids: list[str] | None = None,
        regions: list[str] | None = None,
        max_confidentiality_level: int = 0,
        deny_document_ids: list[str] | None = None,
        temporary_grants: list[dict[str, Any]] | None = None,
        scope_hash: str = "",
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.roles = roles
        self.permissions = permissions
        self.data_scopes = data_scopes or {}
        self.role_ids = role_ids or []
        self.department_ids = department_ids or []
        self.group_ids = group_ids or []
        self.knowledge_base_ids = knowledge_base_ids or []
        self.project_ids = project_ids or []
        self.regions = regions or []
        self.max_confidentiality_level = max_confidentiality_level
        self.deny_document_ids = deny_document_ids or []
        self.temporary_grants = temporary_grants or []
        self.scope_hash = scope_hash

    def has_permission(self, permission: str) -> bool:
        """检查是否具有指定权限（* 仅表示功能权限通配，不表示数据权限放行）"""
        if "*" in self.permissions:
            return True
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """检查是否具有指定角色"""
        return role in self.roles

    def can_access_data(self, resource_type: str, resource_id: str) -> bool:
        """
        检查是否可以访问指定资源
        data_scopes: {"document": ["doc1", "doc2"], "knowledge_base": ["kb1"]}
        """
        if "*" in self.data_scopes.get(resource_type, []):
            return True
        return resource_id in self.data_scopes.get(resource_type, [])

    def get_data_scope_filter(self, resource_type: str) -> list[str] | None:
        """获取指定资源类型的数据范围过滤"""
        scopes = self.data_scopes.get(resource_type, [])
        return None if "*" in scopes else scopes

    def is_super_admin(self) -> bool:
        """是否是超级管理员"""
        return "super_admin" in self.roles

    def is_tenant_admin(self) -> bool:
        """是否是租户管理员"""
        return "tenant_admin" in self.roles

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "roles": self.roles,
            "permissions": self.permissions,
            "data_scopes": self.data_scopes,
            "role_ids": self.role_ids,
            "department_ids": self.department_ids,
            "group_ids": self.group_ids,
            "knowledge_base_ids": self.knowledge_base_ids,
            "project_ids": self.project_ids,
            "regions": self.regions,
            "max_confidentiality_level": self.max_confidentiality_level,
            "deny_document_ids": self.deny_document_ids,
            "temporary_grants": self.temporary_grants,
            "scope_hash": self.scope_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccessContext":
        """从字典创建"""
        return cls(
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            data_scopes=data.get("data_scopes", {}),
            role_ids=data.get("role_ids", []),
            department_ids=data.get("department_ids", []),
            group_ids=data.get("group_ids", []),
            knowledge_base_ids=data.get("knowledge_base_ids", []),
            project_ids=data.get("project_ids", []),
            regions=data.get("regions", []),
            max_confidentiality_level=int(data.get("max_confidentiality_level", 0) or 0),
            deny_document_ids=data.get("deny_document_ids", []),
            temporary_grants=data.get("temporary_grants", []),
            scope_hash=data.get("scope_hash", "") or "",
        )

    @classmethod
    def system(cls, tenant_id: str = "system") -> "AccessContext":
        """创建系统级访问上下文"""
        return cls(
            user_id="system",
            tenant_id=tenant_id,
            roles=["system"],
            permissions=["*"],
            data_scopes={"*": ["*"]},
        )
