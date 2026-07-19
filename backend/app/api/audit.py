"""
成员4：审计路由
实现审计日志、安全事件、登录日志的查询接口
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DBSession, RequiredUser
from app.core.responses import paginated_response, success_response
from app.schemas.common import PaginationParams
from app.services.audit_service import AuditService

audit_router = APIRouter()
router = audit_router  # main.py 兼容别名
@audit_router.get("/audit-logs", tags=["审计"])
async def list_audit_logs_api(
    db: DBSession,
    current_user_id: RequiredUser,
    pagination: Annotated[PaginationParams, Depends()],
    tenant_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
):
    """查询审计日志"""
    service = AuditService(db)
    result = await service.list_audit_logs(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@audit_router.get("/security-events", tags=["审计"])
async def list_security_events_api(
    db: DBSession,
    current_user_id: RequiredUser,
    pagination: Annotated[PaginationParams, Depends()],
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    resolved: bool | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
):
    """查询安全事件"""
    service = AuditService(db)
    result = await service.list_security_events(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        resolved=resolved,
        start_date=start_date,
        end_date=end_date,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@audit_router.post("/security-events/{event_id}/resolve", tags=["审计"])
async def resolve_security_event_api(
    event_id: str,
    db: DBSession,
    current_user_id: RequiredUser,
):
    """标记安全事件已解决"""
    service = AuditService(db)
    await service.resolve_security_event(event_id, current_user_id)
    return success_response(message="标记成功")


@audit_router.get("/login-logs", tags=["审计"])
async def list_login_logs_api(
    db: DBSession,
    current_user_id: RequiredUser,
    pagination: Annotated[PaginationParams, Depends()],
    user_id: str | None = Query(default=None),
    username: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
):
    """查询登录日志"""
    service = AuditService(db)
    result = await service.list_login_logs(
        user_id=user_id,
        username=username,
        success=success,
        start_date=start_date,
        end_date=end_date,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated_response(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )