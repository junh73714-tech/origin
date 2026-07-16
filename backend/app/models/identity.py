"""
成员4：身份认证与组织管理模型
包括部门、用户组、数据范围、临时授权、登录日志等
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


# 用户部门关联表
user_departments = Table(
    "user_departments",
    BaseModel.metadata,
    Column("user_id", String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("department_id", String(64), ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
    Column("is_primary", Boolean, nullable=False, default=False),
)

# 用户组成员关联表
user_group_members = Table(
    "user_group_members",
    BaseModel.metadata,
    Column("user_id", String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", String(64), ForeignKey("user_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime(timezone=True)),
)


class Department(BaseModel):
    """部门模型"""

    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("departments.id", ondelete="SET NULL")
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    parent: Mapped["Department | None"] = relationship(
        "Department", remote_side="Department.id", back_populates="children"
    )
    children: Mapped[list["Department"]] = relationship(
        "Department", back_populates="parent"
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_departments,
        back_populates="departments",
    )

    def __repr__(self) -> str:
        return f"<Department {self.code}: {self.name}>"


class UserGroup(BaseModel):
    """用户组模型"""

    __tablename__ = "user_groups"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    members: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_group_members,
        back_populates="groups",
    )

    def __repr__(self) -> str:
        return f"<UserGroup {self.code}: {self.name}>"


class DataScope(BaseModel):
    """数据范围模型"""

    __tablename__ = "data_scopes"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    def __repr__(self) -> str:
        return f"<DataScope {self.code}: {self.name}>"


class KnowledgeBasePermission(BaseModel):
    """知识库权限模型"""

    __tablename__ = "knowledge_base_permissions"

    knowledge_base_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    role_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("roles.id", ondelete="CASCADE"), nullable=True
    )
    department_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True
    )
    group_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=True
    )
    permission_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_deny: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    effective_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<KnowledgeBasePermission kb={self.knowledge_base_id} type={self.permission_type}>"


class DocumentPermission(BaseModel):
    """文档权限模型"""

    __tablename__ = "document_permissions"

    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    role_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("roles.id", ondelete="CASCADE"), nullable=True
    )
    department_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True
    )
    group_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=True
    )
    permission_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_deny: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidentiality_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    effective_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<DocumentPermission doc={self.document_id} type={self.permission_type}>"


class TemporaryGrant(BaseModel):
    """临时授权模型"""

    __tablename__ = "temporary_grants"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    permission_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiration_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    def __repr__(self) -> str:
        return f"<TemporaryGrant user={self.user_id} resource={self.resource_type}:{self.resource_id}>"


class LoginLog(BaseModel):
    """登录日志模型"""

    __tablename__ = "login_logs"

    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    login_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<LoginLog user={self.username} success={self.success}>"