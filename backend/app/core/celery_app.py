"""
Celery 应用工厂

创建和配置 Celery 应用实例，用于异步任务调度。

成员1/5共责: Celery基础设施
"""
from celery import Celery

from app.core.config import settings

_celery_app: Celery | None = None


def get_celery_app() -> Celery:
    """获取Celery应用单例"""
    global _celery_app
    if _celery_app is None:
        _celery_app = Celery(
            "rag_knowledge",
            broker=settings.celery.resolved_broker_url,
            backend=settings.celery.resolved_result_backend,
        )
        _celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="Asia/Shanghai",
            enable_utc=True,
            task_track_started=True,
            task_acks_late=True,
            worker_prefetch_multiplier=1,
        )
    return _celery_app
