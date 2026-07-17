"""
用户模型
"""
from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class User(BaseModel):
    """用户模型"""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, comment="用户状态: active/disabled/locked")
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True, comment="最后登录时间")

    # 关系
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
    )
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user")
    departments: Mapped[list["Department"]] = relationship(
        "Department",
        secondary="user_departments",
        back_populates="users",
    )
    groups: Mapped[list["UserGroup"]] = relationship(
        "UserGroup",
        secondary="user_group_members",
        back_populates="members",
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


# 延迟导入避免循环引用
from app.models.auth import Role, Session, Permission
from app.models.identity import Department, UserGroup
