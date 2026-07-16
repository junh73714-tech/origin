"""
认证相关模型
包括角色、权限、会话等
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# 关联表
user_roles = Table(
    "user_roles",
    BaseModel.metadata,
    mapped_column("user_id", String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    mapped_column("role_id", String(64), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    BaseModel.metadata,
    mapped_column("role_id", String(64), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    mapped_column("permission_id", String(64), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(BaseModel):
    """权限模型"""

    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # document, knowledge_base, qa, etc.
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, read, update, delete
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关系
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class Role(BaseModel):
    """角色模型"""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)  # 系统内置角色不可删除

    # 关系
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role {self.code}>"


class Session(BaseModel):
    """会话模型"""

    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 最大长度

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session {self.id} user={self.user_id}>"
