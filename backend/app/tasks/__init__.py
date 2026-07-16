"""
Tasks 模块初始化（成员7）
"""
from app.tasks.qa_tasks import (
    generate_candidate_qas,
    consume_outbox_events,
    run_quality_checks,
    auto_expire_qas,
    get_celery_app,
    register_celery_tasks,
)

__all__ = [
    "generate_candidate_qas",
    "consume_outbox_events",
    "run_quality_checks",
    "auto_expire_qas",
    "get_celery_app",
    "register_celery_tasks",
]