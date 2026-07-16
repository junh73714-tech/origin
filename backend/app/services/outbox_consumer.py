"""
Outbox 事件消费服务（成员7）
处理文档版本变更等跨模块事件，确保幂等性
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import OutboxEvent
from app.services.qa_service import qa_service

logger = get_logger(__name__)

# 成员7关注的事件类型
MEMBER7_EVENT_TYPES = [
    "document.version.published",
    "document.paused",
    "document.offlined",
    "document.permission.changed",
]


class OutboxEventConsumer:
    """Outbox 事件消费者"""

    @staticmethod
    async def consume_events(
        db: AsyncSession,
        batch_size: int = 50,
    ) -> dict[str, Any]:
        """
        消费未处理的 Outbox 事件
        确保幂等：已处理的事件不会重复处理
        """
        # 查询未发布的事件
        stmt = (
            select(OutboxEvent)
            .where(
                and_(
                    OutboxEvent.published == False,  # noqa: E712
                    OutboxEvent.event_type.in_(MEMBER7_EVENT_TYPES),
                    OutboxEvent.retry_count < OutboxEvent.max_retries,
                )
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        processed = 0
        failed = 0
        errors: list[dict] = []

        for event in events:
            try:
                await OutboxEventConsumer._process_event(db, event)
                processed += 1
            except Exception as e:
                failed += 1
                errors.append({
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "error": str(e),
                })
                logger.error(
                    "outbox_event_processing_failed",
                    event_id=event.id,
                    event_type=event.event_type,
                    error=str(e),
                )

        await db.flush()
        return {
            "total": len(events),
            "processed": processed,
            "failed": failed,
            "errors": errors,
        }

    @staticmethod
    async def _process_event(db: AsyncSession, event: OutboxEvent) -> None:
        """处理单个 Outbox 事件"""
        event_type = event.event_type
        payload = event.payload or {}
        document_id = payload.get("document_id", "")
        new_version = payload.get("version", payload.get("new_version", 1))
        knowledge_base_id = payload.get("knowledge_base_id", "")

        logger.info(
            "processing_outbox_event",
            event_type=event_type,
            document_id=document_id,
            event_id=event.id,
        )

        if event_type == "document.version.published":
            # 文档新版本发布，标记相关问答为待复核
            affected = await qa_service.handle_document_version_change(
                db,
                document_id=document_id,
                new_version=new_version,
                event_type=event_type,
                user_id="system",
            )
            logger.info(
                "document_version_change_handled",
                document_id=document_id,
                affected_qa_count=len(affected),
            )

        elif event_type == "document.paused":
            # 文档暂停，下线相关问答
            affected = await qa_service.handle_document_version_change(
                db,
                document_id=document_id,
                new_version=new_version,
                event_type=event_type,
                user_id="system",
            )
            logger.info(
                "document_paused_handled",
                document_id=document_id,
                affected_qa_count=len(affected),
            )

        elif event_type == "document.offlined":
            # 文档下线，下线相关问答
            affected = await qa_service.handle_document_version_change(
                db,
                document_id=document_id,
                new_version=new_version,
                event_type=event_type,
                user_id="system",
            )
            logger.info(
                "document_offlined_handled",
                document_id=document_id,
                affected_qa_count=len(affected),
            )

        elif event_type == "document.permission.changed":
            # 文档权限变更，标记相关问答为待复核
            affected = await qa_service.handle_document_version_change(
                db,
                document_id=document_id,
                new_version=new_version,
                event_type=event_type,
                user_id="system",
            )
            logger.info(
                "document_permission_change_handled",
                document_id=document_id,
                affected_qa_count=len(affected),
            )

        # 标记事件为已处理（幂等保证）
        event.published = True
        event.published_at = datetime.now(timezone.utc).isoformat()

    @staticmethod
    async def handle_single_event(
        db: AsyncSession,
        event_type: str,
        document_id: str,
        new_version: int = 1,
        payload: dict | None = None,
    ) -> dict[str, Any]:
        """
        直接处理单个事件（不通过 Outbox 表）
        用于实时事件处理场景
        """
        affected = await qa_service.handle_document_version_change(
            db,
            document_id=document_id,
            new_version=new_version,
            event_type=event_type,
            user_id="system",
        )

        return {
            "event_type": event_type,
            "document_id": document_id,
            "affected_qa_count": len(affected),
            "affected_qa_ids": [qa.id for qa in affected],
        }

    @staticmethod
    async def get_pending_event_count(db: AsyncSession) -> int:
        """获取待处理事件数量"""
        stmt = select(OutboxEvent).where(
            and_(
                OutboxEvent.published == False,  # noqa: E712
                OutboxEvent.event_type.in_(MEMBER7_EVENT_TYPES),
            )
        )
        result = await db.execute(stmt)
        return len(list(result.scalars().all()))


# 单例
outbox_event_consumer = OutboxEventConsumer()