"""
公共模型基类
定义所有数据模型的公共字段
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_id() -> str:
    """生成唯一ID（32位UUID，去连字符）"""
    return uuid.uuid4().hex


class TimestampMixin:
    """时间戳混入"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """租户混入"""

    tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )


class SoftDeleteMixin:
    """软删除混入"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    deleted_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )


class AuditMixin:
    """审计混入"""

    created_by: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )


class BaseModel(Base, TimestampMixin, TenantMixin, AuditMixin):
    """基础模型 -- 所有业务模型的基类"""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_id,
        comment="主键ID",
    )

    def to_dict(self, exclude: list[str] | None = None) -> dict[str, Any]:
        """转换为字典"""
        exclude = exclude or []
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        return result

    def to_dict_safe(self) -> dict[str, Any]:
        """安全转换为字典（排除敏感字段）"""
        return self.to_dict(exclude=["password_hash"])
