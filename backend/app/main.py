"""
FastAPI 应用工厂
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import setup_logging, get_logger
from app.core.middleware import setup_middleware
from app.core.responses import success_response, error_response

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动
    logger.info("application_starting", app_name=settings.name)
    setup_logging()
    await init_db()
    logger.info("application_started", app_name=settings.name)

    yield

    # 关闭
    logger.info("application_stopping", app_name=settings.name)
    await close_db()
    logger.info("application_stopped", app_name=settings.name)


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""

    app = FastAPI(
        title=settings.name,
        description="企业级混合检索 RAG 知识问答平台 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 配置中间件
    setup_middleware(app)

    # 注册路由
    register_routes(app)

    # 注册异常处理器
    register_exception_handlers(app)

    return app


def register_routes(app: FastAPI) -> None:
    """注册路由"""
    from app.api.common.health import router as health_router
    from app.api.auth import router as auth_router
    from app.api.documents import router as documents_router
    from app.api.chunks import router as chunks_router
    from app.api.knowledge_bases import router as knowledge_bases_router
    from app.api.qa import router as qa_router
    from app.api.feedback import router as feedback_router
    from app.api.evaluation import router as evaluation_router
    from app.api.index_tasks import router as index_tasks_router

    # 健康检查
    app.include_router(health_router, prefix="/api/v1", tags=["健康检查"])

    # 认证
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])

    # 知识库
    app.include_router(knowledge_bases_router, prefix="/api/v1/knowledge-bases", tags=["知识库"])

    # 文档
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["文档"])

    # Chunk
    app.include_router(chunks_router, prefix="/api/v1/chunks", tags=["文档片段"])

    # 索引任务
    app.include_router(index_tasks_router, prefix="/api/v1/index-tasks", tags=["索引任务"])

    # 问答
    app.include_router(qa_router, prefix="/api/v1/qa", tags=["问答"])

    # 反馈
    app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["反馈"])

    # 评估
    app.include_router(evaluation_router, prefix="/api/v1", tags=["评估"])

    # 监控指标端点
    from app.monitoring import metrics_endpoint, init_monitoring
    init_monitoring(settings.app.name, "0.1.0")
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])


def register_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器"""
    from fastapi import Request, status
    from fastapi.responses import JSONResponse

    from app.core.exceptions import (
        RAGKnowledgeException,
        AuthenticationError,
        AuthorizationError,
        ResourceNotFoundError,
        ValidationError,
    )

    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )

    @app.exception_handler(AuthorizationError)
    async def authz_exception_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )

    @app.exception_handler(ResourceNotFoundError)
    async def not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )

    @app.exception_handler(RAGKnowledgeException)
    async def rag_exception_handler(request: Request, exc: RAGKnowledgeException):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )


# 创建应用实例
app = create_app()