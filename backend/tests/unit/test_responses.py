"""
响应测试
"""
import pytest
from pydantic import BaseModel

from app.core.responses import (
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    PaginatedData,
    success_response,
    error_response,
    paginated_response,
)


def test_success_response():
    """测试成功响应"""
    response = success_response(
        data={"id": "123", "name": "test"},
        message="操作成功",
        request_id="req_123",
    )

    assert response.success is True
    assert response.data == {"id": "123", "name": "test"}
    assert response.message == "操作成功"
    assert response.request_id == "req_123"


def test_error_response():
    """测试错误响应"""
    response = error_response(
        code="VALIDATION_ERROR",
        message="数据验证失败",
        details={"field": "name"},
        request_id="req_123",
    )

    assert response.success is False
    assert response.error.code == "VALIDATION_ERROR"
    assert response.error.message == "数据验证失败"
    assert response.error.details == {"field": "name"}


def test_paginated_data():
    """测试分页数据"""
    items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
    paginated = PaginatedData.create(
        items=items,
        total=10,
        page=1,
        page_size=3,
    )

    assert paginated.items == items
    assert paginated.total == 10
    assert paginated.page == 1
    assert paginated.page_size == 3
    assert paginated.total_pages == 4


def test_paginated_response():
    """测试分页响应"""
    items = [{"id": "1"}, {"id": "2"}]
    response = paginated_response(
        items=items,
        total=5,
        page=1,
        page_size=2,
    )

    assert response.success is True
    assert response.data.total == 5
    assert len(response.data.items) == 2
