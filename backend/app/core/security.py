"""
安全工具模块
提供密码哈希、JWT 令牌、访问上下文等安全功能
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """哈希密码"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


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
    包含当前请求的用户信息和权限范围
    """

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        roles: list[str],
        permissions: list[str],
        data_scopes: dict[str, list[str]] | None = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.roles = roles
        self.permissions = permissions
        self.data_scopes = data_scopes or {}

    def has_permission(self, permission: str) -> bool:
        """检查是否具有指定权限，支持通配符 *"""
        # 通配符表示拥有所有权限
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
