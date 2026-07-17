"""
认证相关 Schema
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import BaseSchema


# ============ 请求 Schema ============

class PermissionCreate(BaseSchema):
    """创建权限请求"""
    name: str = Field(..., description="权限名称")
    code: str = Field(..., description="权限编码")
    resource_type: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")
    description: str | None = Field(default=None, description="权限描述")


class RoleCreate(BaseSchema):
    """创建角色请求"""
    name: str = Field(..., description="角色名称")
    code: str = Field(..., description="角色编码")
    description: str | None = Field(default=None, description="角色描述")
    is_system: bool = Field(default=False, description="是否系统角色")


class LoginRequest(BaseSchema):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=100, description="用户名或邮箱")
    password: str = Field(..., min_length=6, description="密码")


class RefreshTokenRequest(BaseSchema):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class RegisterRequest(BaseSchema):
    """注册请求"""
    email: EmailStr = Field(..., description="邮箱")
    username: str = Field(..., min_length=3, max_length=100, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    full_name: str | None = Field(default=None, max_length=100, description="姓名")


class ChangePasswordRequest(BaseSchema):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class ResetPasswordRequest(BaseSchema):
    """重置密码请求"""
    email: EmailStr = Field(..., description="邮箱")


# ============ 响应 Schema ============

class TokenResponse(BaseSchema):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseSchema):
    """用户响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    full_name: str | None = None
    phone: str | None = None
    is_active: bool
    is_superuser: bool
    status: str = "active"
    last_login_at: datetime | None = None
    department_id: str | None = None
    department_name: str | None = None
    created_at: datetime
    updated_at: datetime


class UserDetailResponse(UserResponse):
    """用户详情响应"""
    roles: list["RoleResponse"] = []


class RoleResponse(BaseSchema):
    """角色响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    description: str | None = None
    is_system: bool
    user_count: int = 0
    permission_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PermissionResponse(BaseSchema):
    """权限响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    resource_type: str
    action: str
    description: str | None = None


class LoginResponse(BaseSchema):
    """登录响应"""
    user: UserResponse
    tokens: TokenResponse


# ============ 内部 Schema ============

class AccessTokenPayload(BaseSchema):
    """访问令牌载荷"""
    sub: str  # user_id
    tenant_id: str
    roles: list[str] = []
    permissions: list[str] = []
    data_scopes: dict[str, list[str]] = {}


class RefreshTokenPayload(BaseSchema):
    """刷新令牌载荷"""
    sub: str  # user_id
    session_id: str
