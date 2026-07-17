"""
公共 Schema 模块
定义通用数据 Schema
"""
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """基础 Schema"""
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """带时间戳的 Schema"""
    id: str
    created_at: datetime
    updated_at: datetime


class TenantSchema(BaseSchema):
    """带租户的 Schema"""
    tenant_id: str


class AuditSchema(TenantSchema):
    """带审计字段的 Schema"""
    created_by: str
    updated_by: str | None = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class SortParams(BaseModel):
    """排序参数"""
    sort_by: str | None = Field(default=None, description="排序字段")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")


class FilterParams(BaseModel):
    """筛选参数"""
    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="状态筛选")
    start_date: datetime | None = Field(default=None, description="开始日期")
    end_date: datetime | None = Field(default=None, description="结束日期")


class ListResponse(BaseSchema, Generic[T]):
    """列表响应"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedData(BaseSchema, Generic[T]):
    """分页数据"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedData[T]":
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class BulkOperationResult(BaseSchema):
    """批量操作结果"""
    total: int
    success: int
    failed: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class HealthCheckResponse(BaseSchema):
    """健康检查响应"""
    status: str
    version: str
    timestamp: datetime
    services: dict[str, dict[str, Any]] = Field(default_factory=dict)
