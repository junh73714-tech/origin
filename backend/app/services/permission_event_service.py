"""
成员4：权限变更事件服务
实现权限变化的Outbox事件生成和处理
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import OutboxEvent

logger = get_logger(__name__)

PERMISSION_EVENT_TYPES = {
    "user_changed": "permission.user.changed",
    "role_changed": "permission.role.changed",
    "knowledge_base_changed": "permission.knowledge_base.changed",
    "document_changed": "permission.document.changed",
    "temporary_grant_expired": "temporary_grant.expired",
}


class PermissionEventService:
    """权限事件服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_permission_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        tenant_id: str,
        payload: dict[str, Any],
        user_id: str = "system",
    ) -> OutboxEvent:
        """创建权限事件"""
        event = OutboxEvent(
            id=f"evt_{uuid.uuid4().hex[:16]}",
            tenant_id=tenant_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            published=False,
            published_at=None,
            retry_count=0,
            max_retries=3,
            error_message=None,
            created_by=user_id,
        )
        self.db.add(event)
        await self.db.flush()

        logger.info("permission_event_created", event_type=event_type, aggregate_id=aggregate_id)

        return event

    async def record_user_changed(
        self,
        user_id: str,
        tenant_id: str = "default",
        changed_by: str = "system",
        changes: dict[str, Any] | None = None,
    ) -> OutboxEvent:
        """记录用户变更事件"""
        event_type = PERMISSION_EVENT_TYPES["user_changed"]
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "changed_by": changed_by,
            "changes": changes or {},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        return await self.create_permission_event(
            event_type=event_type,
            aggregate_type="user",
            aggregate_id=user_id,
            tenant_id=tenant_id,
            payload=payload,
            user_id=changed_by,
        )

    async def record_role_changed(
        self,
        role_id: str,
        tenant_id: str = "default",
        changed_by: str = "system",
        changes: dict[str, Any] | None = None,
    ) -> OutboxEvent:
        """记录角色变更事件"""
        event_type = PERMISSION_EVENT_TYPES["role_changed"]
        payload = {
            "role_id": role_id,
            "tenant_id": tenant_id,
            "changed_by": changed_by,
            "changes": changes or {},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        return await self.create_permission_event(
            event_type=event_type,
            aggregate_type="role",
            aggregate_id=role_id,
            tenant_id=tenant_id,
            payload=payload,
            user_id=changed_by,
        )

    async def record_knowledge_base_changed(
        self,
        knowledge_base_id: str,
        tenant_id: str = "default",
        changed_by: str = "system",
        changes: dict[str, Any] | None = None,
    ) -> OutboxEvent:
        """记录知识库权限变更事件"""
        event_type = PERMISSION_EVENT_TYPES["knowledge_base_changed"]
        payload = {
            "knowledge_base_id": knowledge_base_id,
            "tenant_id": tenant_id,
            "changed_by": changed_by,
            "changes": changes or {},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        return await self.create_permission_event(
            event_type=event_type,
            aggregate_type="knowledge_base",
            aggregate_id=knowledge_base_id,
            tenant_id=tenant_id,
            payload=payload,
            user_id=changed_by,
        )

    async def record_document_changed(
        self,
        document_id: str,
        tenant_id: str = "default",
        changed_by: str = "system",
        changes: dict[str, Any] | None = None,
    ) -> OutboxEvent:
        """记录文档权限变更事件"""
        event_type = PERMISSION_EVENT_TYPES["document_changed"]
        payload = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "changed_by": changed_by,
            "changes": changes or {},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        return await self.create_permission_event(
            event_type=event_type,
            aggregate_type="document",
            aggregate_id=document_id,
            tenant_id=tenant_id,
            payload=payload,
            user_id=changed_by,
        )

    async def record_temporary_grant_expired(
        self,
        grant_id: str,
        user_id: str,
        tenant_id: str = "default",
    ) -> OutboxEvent:
        """记录临时授权过期事件"""
        event_type = PERMISSION_EVENT_TYPES["temporary_grant_expired"]
        payload = {
            "grant_id": grant_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "expired_at": datetime.now(timezone.utc).isoformat(),
        }

        return await self.create_permission_event(
            event_type=event_type,
            aggregate_type="temporary_grant",
            aggregate_id=grant_id,
            tenant_id=tenant_id,
            payload=payload,
            user_id="system",
        )

    async def mark_event_published(self, event_id: str) -> None:
        """标记事件已发布"""
        from sqlalchemy import select, update

        result = await self.db.execute(
            select(OutboxEvent).filter(OutboxEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return

        event.published = True
        event.published_at = datetime.now(timezone.utc).isoformat()
        await self.db.flush()

        logger.info("permission_event_published", event_id=event_id)

    async def get_unpublished_events(self, limit: int = 100) -> list[OutboxEvent]:
        """获取未发布的事件"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(OutboxEvent)
            .filter(OutboxEvent.published.is_(False))
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def increment_retry_count(self, event_id: str, error_message: str) -> None:
        """增加事件重试计数"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(OutboxEvent).filter(OutboxEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return

        event.retry_count = event.retry_count + 1
        event.error_message = error_message
        await self.db.flush()

        logger.warning("permission_event_retry", event_id=event_id, retry_count=event.retry_count)