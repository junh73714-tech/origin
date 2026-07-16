"""
结构化日志模块
统一日志配置，支持 JSON 格式输出
"""
import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """配置结构化日志"""

    # 配置标准日志处理器
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # 配置 structlog
    structlog.configure(
        processors=[
            # 添加时间戳
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            # 添加请求上下文
            structlog.contextvars.merge_contextvars,
            # 处理异常
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON 输出
            structlog.processors.JSONRenderer()
            if settings.environment != "development"
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取日志记录器"""
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


class LoggerMixin:
    """日志混入类，为其他类提供日志功能"""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        if not hasattr(self, "_logger"):
            name = f"{self.__class__.__module__}.{self.__class__.__name__}"
            self._logger = get_logger(name)
        return self._logger


def log_request(
    logger: structlog.stdlib.BoundLogger,
    request_id: str,
    method: str,
    path: str,
    user_id: str | None = None,
    **extra: Any,
) -> None:
    """记录请求日志"""
    logger.info(
        "request_started",
        request_id=request_id,
        method=method,
        path=path,
        user_id=user_id,
        **extra,
    )


def log_response(
    logger: structlog.stdlib.BoundLogger,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra: Any,
) -> None:
    """记录响应日志"""
    log_level = "info" if status_code < 400 else "warning"
    getattr(logger, log_level)(
        "request_completed",
        request_id=request_id,
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **extra,
    )


def log_audit(
    logger: structlog.stdlib.BoundLogger,
    action: str,
    resource_type: str,
    resource_id: str,
    user_id: str,
    tenant_id: str,
    result: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """记录审计日志"""
    logger.info(
        "audit_event",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        tenant_id=tenant_id,
        result=result,
        details=details or {},
    )
