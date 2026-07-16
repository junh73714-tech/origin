"""
成员4：身份认证与组织管理 Schema
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BaseSchema


# ============ 部门 Schema ============

class DepartmentCreate(BaseSchema):
    """创建部门请求"""
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    code: str = Field(..., min_length=1, max_length=50, description="部门编码")
    parent_id: str | None = Field(default=None, description="父部门ID")
    description: str | None = Field(default=None, description="部门描述")
    sort_order: int = Field(default=0, description="排序顺序")


class DepartmentUpdate(BaseSchema):
    """更新部门请求"""
    name: str | None = Field(default=None, max_length=100, description="部门名称")
    code: str | None = Field(default=None, max_length=50, description="部门编码")
    parent_id: str | None = Field(default=None, description="父部门ID")
    description: str | None = Field(default=None, description="部门描述")
    status: str | None = Field(default=None, description="部门状态")
    sort_order: int | None = Field(default=None, description="排序顺序")


class DepartmentResponse(BaseSchema):
    """部门响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    code: str
    parent_id: str | None = None
    description: str | None = None
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str | None = None


class DepartmentTreeResponse(DepartmentResponse):
    """部门树响应"""
    children: list["DepartmentTreeResponse"] = []


# ============ 用户组 Schema ============

class UserGroupCreate(BaseSchema):
    """创建用户组请求"""
    name: str = Field(..., min_length=1, max_length=100, description="用户组名称")
    code: str = Field(..., min_length=1, max_length=50, description="用户组编码")
    description: str | None = Field(default=None, description="用户组描述")


class UserGroupUpdate(BaseSchema):
    """更新用户组请求"""
    name: str | None = Field(default=None, max_length=100, description="用户组名称")
    code: str | None = Field(default=None, max_length=50, description="用户组编码")
    description: str | None = Field(default=None, description="用户组描述")
    status: str | None = Field(default=None, description="用户组状态")


class UserGroupResponse(BaseSchema):
    """用户组响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    code: str
    description: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str | None = None


# ============ 用户组织关系 Schema ============

class UserDepartmentAssign(BaseSchema):
    """分配用户到部门请求"""
    user_id: str = Field(..., description="用户ID")
    department_id: str = Field(..., description="部门ID")
    is_primary: bool = Field(default=False, description="是否主部门")


class UserGroupMemberAdd(BaseSchema):
    """添加用户组成员请求"""
    user_id: str = Field(..., description="用户ID")
    group_id: str = Field(..., description="用户组ID")


# ============ 数据权限 Schema ============

class DataScopeCreate(BaseSchema):
    """创建数据范围请求"""
    name: str = Field(..., min_length=1, max_length=100, description="数据范围名称")
    code: str = Field(..., min_length=1, max_length=50, description="数据范围编码")
    scope_type: str = Field(..., description="数据范围类型")
    description: str | None = Field(default=None, description="数据范围描述")


class DataScopeResponse(BaseSchema):
    """数据范围响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    code: str
    scope_type: str
    description: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


# ============ 知识库权限 Schema ============

class KnowledgeBasePermissionCreate(BaseSchema):
    """创建知识库权限请求"""
    knowledge_base_id: str = Field(..., description="知识库ID")
    user_id: str | None = Field(default=None, description="用户ID")
    role_id: str | None = Field(default=None, description="角色ID")
    department_id: str | None = Field(default=None, description="部门ID")
    group_id: str | None = Field(default=None, description="用户组ID")
    permission_type: str = Field(..., description="权限类型")
    is_deny: bool = Field(default=False, description="是否拒绝")
    effective_time: datetime | None = Field(default=None, description="生效时间")
    expiration_time: datetime | None = Field(default=None, description="失效时间")


class KnowledgeBasePermissionResponse(BaseSchema):
    """知识库权限响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    knowledge_base_id: str
    user_id: str | None = None
    role_id: str | None = None
    department_id: str | None = None
    group_id: str | None = None
    permission_type: str
    is_deny: bool
    effective_time: datetime | None = None
    expiration_time: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ============ 文档权限 Schema ============

class DocumentPermissionCreate(BaseSchema):
    """创建文档权限请求"""
    document_id: str = Field(..., description="文档ID")
    user_id: str | None = Field(default=None, description="用户ID")
    role_id: str | None = Field(default=None, description="角色ID")
    department_id: str | None = Field(default=None, description="部门ID")
    group_id: str | None = Field(default=None, description="用户组ID")
    permission_type: str = Field(..., description="权限类型")
    is_deny: bool = Field(default=False, description="是否拒绝")
    confidentiality_level: int = Field(default=0, description="文档密级")
    effective_time: datetime | None = Field(default=None, description="生效时间")
    expiration_time: datetime | None = Field(default=None, description="失效时间")


class DocumentPermissionResponse(BaseSchema):
    """文档权限响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    document_id: str
    user_id: str | None = None
    role_id: str | None = None
    department_id: str | None = None
    group_id: str | None = None
    permission_type: str
    is_deny: bool
    confidentiality_level: int
    effective_time: datetime | None = None
    expiration_time: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ============ 临时授权 Schema ============

class TemporaryGrantCreate(BaseSchema):
    """创建临时授权请求"""
    user_id: str = Field(..., description="用户ID")
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    permission_type: str = Field(..., description="权限类型")
    reason: str | None = Field(default=None, description="授权原因")
    effective_time: datetime = Field(..., description="生效时间")
    expiration_time: datetime = Field(..., description="失效时间")


class TemporaryGrantUpdate(BaseSchema):
    """更新临时授权请求"""
    status: str | None = Field(default=None, description="授权状态")
    reason: str | None = Field(default=None, description="授权原因")


class TemporaryGrantResponse(BaseSchema):
    """临时授权响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    user_id: str
    resource_type: str
    resource_id: str
    permission_type: str
    reason: str | None = None
    effective_time: datetime
    expiration_time: datetime
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str | None = None


# ============ 登录日志 Schema ============

class LoginLogResponse(BaseSchema):
    """登录日志响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    user_id: str | None = None
    username: str
    success: bool
    failure_reason: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    login_time: datetime
    session_id: str | None = None


# ============ 权限检查 Schema ============

class PermissionCheckRequest(BaseSchema):
    """权限检查请求"""
    action: str = Field(..., description="操作权限编码")
    resource_type: str | None = Field(default=None, description="资源类型")
    resource_id: str | None = Field(default=None, description="资源ID")


class PermissionCheckResponse(BaseSchema):
    """权限检查响应"""
    allowed: bool
    permission: str
    resource_type: str | None = None
    resource_id: str | None = None
    reason: str | None = None


# ============ AccessContext Schema ============

class TemporaryGrantInfo(BaseSchema):
    """临时授权信息"""
    resource_type: str
    resource_id: str
    permission_type: str
    effective_time: datetime
    expiration_time: datetime


class AccessContextResponse(BaseSchema):
    """访问上下文响应"""
    tenant_id: str
    user_id: str
    role_ids: list[str]
    department_ids: list[str]
    group_ids: list[str]
    knowledge_base_ids: list[str]
    project_ids: list[str]
    regions: list[str]
    max_confidentiality_level: int
    deny_document_ids: list[str]
    temporary_grants: list[TemporaryGrantInfo]
    scope_hash: str


# ============ 检索过滤 Schema ============

class RetrievalFilter(BaseSchema):
    """检索过滤条件"""
    tenant_id: str
    user_id: str
    knowledge_base_ids: list[str]
    department_ids: list[str]
    group_ids: list[str]
    project_ids: list[str]
    regions: list[str]
    max_confidentiality_level: int
    deny_document_ids: list[str]
    allow_document_ids: list[str]
    effective_temporary_grants: list[TemporaryGrantInfo]
    require_published: bool = False
    require_current_version: bool = False
    exclude_paused: bool = False
    exclude_offlined: bool = False
    exclude_expired: bool = False
    scope_hash: str


class OpenSearchFilterDSL(BaseSchema):
    """OpenSearch 过滤 DSL"""
    bool: dict[str, Any]


class PostgreSQLFilter(BaseSchema):
    """PostgreSQL 过滤条件"""
    where_clause: str
    params: dict[str, Any]