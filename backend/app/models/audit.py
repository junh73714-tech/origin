"""
审计相关模型
包括审计日志、安全事件等
"""
from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AuditLog(BaseModel):
    """审计日志模型"""

    __tablename__ = "audit_logs"

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    request_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_tenant_time", "tenant_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type}:{self.resource_id}>"


class SecurityEvent(BaseModel):
    """安全事件模型"""

    __tablename__ = "security_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_security_events_severity_resolved", "severity", "resolved"),
        Index("ix_security_events_time", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SecurityEvent {self.event_type} [{self.severity}]>"


class OutboxEvent(BaseModel):
    """Outbox 事件模型（用于跨模块事件传递）"""

    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False)  # document, qa, user, etc.
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published: Mapped[bool] = mapped_column(default=False, nullable=False)
    published_at: Mapped[str | None] = mapped_column(nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_outbox_events_unpublished", "published", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<OutboxEvent {self.event_type} {self.aggregate_id}>"
