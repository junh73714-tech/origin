"""
中间件模块
包含请求ID追踪、CORS、异常处理等中间件
"""
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger, log_request, log_response

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取或生成请求 ID
        request_id = request.headers.get("X-Request-ID") or f"req_{int(time.time() * 1000)}"

        # 添加到请求状态
        request.state.request_id = request_id

        # 添加到响应头
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class TraceIDMiddleware(BaseHTTPMiddleware):
    """追踪 ID 中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取或生成追踪 ID
        trace_id = request.headers.get("X-Trace-ID") or f"trace_{int(time.time() * 1000)}"

        # 添加到请求状态
        request.state.trace_id = trace_id

        # 添加到响应头
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 获取请求信息
        request_id = getattr(request.state, "request_id", None)
        method = request.method
        path = request.url.path

        # 提取用户 ID（如果已认证）
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)

        # 记录请求开始
        log_request(
            logger,
            request_id=request_id or "",
            method=method,
            path=path,
            user_id=user_id,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )

        # 处理请求
        response = await call_next(request)

        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000

        # 记录响应
        log_response(
            logger,
            request_id=request_id or "",
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        return response


def setup_middleware(app) -> None:
    """配置所有中间件"""

    # CORS 中间件
    from app.core.config import settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求 ID 中间件
    app.add_middleware(RequestIDMiddleware)

    # 追踪 ID 中间件
    app.add_middleware(TraceIDMiddleware)

    # 日志中间件
    app.add_middleware(LoggingMiddleware)
