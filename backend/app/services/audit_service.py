"""
成员4：审计服务
实现审计日志、安全事件、登录日志的管理和查询
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import AuditLog, SecurityEvent
from app.models.identity import LoginLog
from app.schemas.common import PaginatedData

logger = get_logger(__name__)


class AuditService:
    """审计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_audit_log(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        method: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        duration_ms: int | None = None,
        request_body: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """创建审计日志"""
        audit_log = AuditLog(
            id=f"audit_{uuid.uuid4().hex[:16]}",
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            request_body=request_body,
            response_body=response_body,
            details=details,
            created_by=user_id,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info("audit_log_created", action=action, resource_type=resource_type, resource_id=resource_id)

    async def list_audit_logs(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedData[dict[str, Any]]:
        """查询审计日志"""
        query = select(AuditLog).filter(AuditLog.deleted_at.is_(None))

        if tenant_id:
            query = query.filter(AuditLog.tenant_id == tenant_id)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if action:
            query = query.filter(AuditLog.action == action)

        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)

        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)

        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        count_query = select(func.count(AuditLog.id)).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        items = [log.to_dict() for log in logs]

        return PaginatedData.create(items, total, page, page_size)

    async def create_security_event(
        self,
        event_type: str,
        severity: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        ip_address: str | None = None,
        description: str = "",
        details: dict[str, Any] | None = None,
        created_by: str = "system",
    ) -> None:
        """创建安全事件"""
        security_event = SecurityEvent(
            id=f"sec_{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            description=description,
            details=details,
            resolved=False,
            created_by=created_by,
        )
        self.db.add(security_event)
        await self.db.flush()

        logger.warning("security_event_created", event_type=event_type, severity=severity, description=description)

    async def list_security_events(
        self,
        event_type: str | None = None,
        severity: str | None = None,
        user_id: str | None = None,
        resolved: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedData[dict[str, Any]]:
        """查询安全事件"""
        query = select(SecurityEvent).filter(SecurityEvent.deleted_at.is_(None))

        if event_type:
            query = query.filter(SecurityEvent.event_type == event_type)

        if severity:
            query = query.filter(SecurityEvent.severity == severity)

        if user_id:
            query = query.filter(SecurityEvent.user_id == user_id)

        if resolved is not None:
            query = query.filter(SecurityEvent.resolved == resolved)

        if start_date:
            query = query.filter(SecurityEvent.created_at >= start_date)

        if end_date:
            query = query.filter(SecurityEvent.created_at <= end_date)

        count_query = select(func.count(SecurityEvent.id)).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(SecurityEvent.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        events = result.scalars().all()

        items = [event.to_dict() for event in events]

        return PaginatedData.create(items, total, page, page_size)

    async def resolve_security_event(
        self,
        event_id: str,
        resolved_by: str,
    ) -> None:
        """标记安全事件已解决"""
        result = await self.db.execute(
            select(SecurityEvent)
            .filter(
                and_(
                    SecurityEvent.id == event_id,
                    SecurityEvent.deleted_at.is_(None),
                )
            )
        )
        event = result.scalar_one_or_none()
        if not event:
            return

        event.resolved = True
        event.resolved_at = datetime.now(timezone.utc).isoformat()
        event.resolved_by = resolved_by
        await self.db.flush()

        logger.info("security_event_resolved", event_id=event_id)

    async def list_login_logs(
        self,
        user_id: str | None = None,
        username: str | None = None,
        success: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedData[dict[str, Any]]:
        """查询登录日志"""
        query = select(LoginLog).filter(LoginLog.deleted_at.is_(None))

        if user_id:
            query = query.filter(LoginLog.user_id == user_id)

        if username:
            query = query.filter(LoginLog.username == username)

        if success is not None:
            query = query.filter(LoginLog.success == success)

        if start_date:
            query = query.filter(LoginLog.login_time >= start_date)

        if end_date:
            query = query.filter(LoginLog.login_time <= end_date)

        count_query = select(func.count(LoginLog.id)).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(LoginLog.login_time.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        items = [log.to_dict() for log in logs]

        return PaginatedData.create(items, total, page, page_size)

    async def log_authorization_denied(
        self,
        user_id: str | None,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
        reason: str = "",
    ) -> None:
        """记录授权拒绝事件"""
        await self.create_audit_log(
            tenant_id=tenant_id,
            user_id=user_id or "anonymous",
            action=f"authorization.denied.{action}",
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
            details={"reason": reason},
        )

        await self.create_security_event(
            event_type="authorization_denied",
            severity="medium",
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            description=f"用户 {user_id} 尝试访问未授权资源: {resource_type}:{resource_id}",
            details={
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "reason": reason,
            },
        )

    async def log_data_scope_violation(
        self,
        user_id: str | None,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """记录数据范围越权事件"""
        await self.create_audit_log(
            tenant_id=tenant_id,
            user_id=user_id or "anonymous",
            action="data_scope.violation",
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
        )

        await self.create_security_event(
            event_type="data_scope_violation",
            severity="high",
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            description=f"用户 {user_id} 越权访问数据: {resource_type}:{resource_id}",
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )

    async def log_id_guessing_attempt(
        self,
        user_id: str | None,
        tenant_id: str,
        resource_type: str,
        guessed_id: str,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """记录ID猜测攻击事件"""
        await self.create_audit_log(
            tenant_id=tenant_id,
            user_id=user_id or "anonymous",
            action="security.id_guessing",
            resource_type=resource_type,
            resource_id=guessed_id,
            request_id=request_id,
            ip_address=ip_address,
        )

        await self.create_security_event(
            event_type="id_guessing_attempt",
            severity="high",
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            description=f"检测到ID猜测攻击: 用户 {user_id} 尝试访问 {resource_type}:{guessed_id}",
            details={
                "resource_type": resource_type,
                "guessed_id": guessed_id,
            },
        )