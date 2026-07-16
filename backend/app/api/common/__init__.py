"""
公共 API 路由初始化
"""
from app.api.common.health import router as health_router

__all__ = ["health_router"]
