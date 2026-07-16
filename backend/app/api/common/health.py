"""
健康检查路由
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.core.responses import success_response
from app.schemas.common import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request) -> HealthCheckResponse:
    """
    健康检查接口
    返回应用状态和依赖服务状态
    """
    services = {}

    # 检查数据库
    try:
        from sqlalchemy import text
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = {"status": "healthy"}
    except Exception as e:
        services["database"] = {"status": "unhealthy", "error": str(e)}

    # 检查 Redis
    try:
        from app.core.config import settings
        import redis.asyncio as redis
        r = redis.from_url(settings.redis.url)
        await r.ping()
        await r.aclose()
        services["redis"] = {"status": "healthy"}
    except Exception as e:
        services["redis"] = {"status": "unhealthy", "error": str(e)}

    # 检查 MinIO
    try:
        # 简化的 MinIO 检查
        services["minio"] = {"status": "not_implemented"}
    except Exception as e:
        services["minio"] = {"status": "unhealthy", "error": str(e)}

    overall_status = "healthy" if all(
        s.get("status") == "healthy" for s in services.values()
    ) else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        services=services,
    )


@router.get("/ready")
async def readiness_check(request: Request):
    """
    就绪检查接口
    用于 Kubernetes readiness probe
    """
    # 就绪检查
    try:
        from sqlalchemy import text
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return success_response(data={"ready": True})
    except Exception:
        return success_response(data={"ready": False})


@router.get("/live")
async def liveness_check():
    """
    存活检查接口
    用于 Kubernetes liveness probe
    """
    return success_response(data={"alive": True})
