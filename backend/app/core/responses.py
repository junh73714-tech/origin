"""
统一响应模块
定义 API 统一成功和失败响应格式
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# 泛型类型
T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """统一成功响应"""

    success: bool = True
    data: T | None = None
    message: str = "操作成功"
    request_id: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "123", "name": "example"},
                "message": "操作成功",
                "request_id": "req_abc123",
            }
        }


class ErrorDetail(BaseModel):
    """错误详情"""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """统一失败响应"""

    success: bool = False
    error: ErrorDetail
    request_id: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "数据验证失败",
                    "details": {"field": "name", "reason": "不能为空"},
                },
                "request_id": "req_abc123",
            }
        }


class PaginatedData(BaseModel, Generic[T]):
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
        """创建分页数据"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    success: bool = True
    data: PaginatedData[T]
    message: str = "查询成功"
    request_id: str | None = None


def success_response(
    data: T | None = None,
    message: str = "操作成功",
    request_id: str | None = None,
) -> SuccessResponse[T]:
    """创建成功响应"""
    return SuccessResponse(
        success=True,
        data=data,
        message=message,
        request_id=request_id,
    )


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(
        success=False,
        error=ErrorDetail(
            code=code,
            message=message,
            details=details or {},
        ),
        request_id=request_id,
    )


def paginated_response(
    items: list[T],
    total: int,
    page: int,
    page_size: int,
    message: str = "查询成功",
    request_id: str | None = None,
) -> PaginatedResponse[T]:
    """创建分页响应"""
    return PaginatedResponse(
        success=True,
        data=PaginatedData.create(items, total, page, page_size),
        message=message,
        request_id=request_id,
    )
