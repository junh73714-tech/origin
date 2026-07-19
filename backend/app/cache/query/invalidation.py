"""Outbox 事件幂等缓存失效。"""
from __future__ import annotations

from typing import Any

from app.cache.query.store import QueryAnswerCache, default_query_cache
from app.core.logging import get_logger

logger = get_logger(__name__)

PERMISSION_EVENTS = {
    "permission.user.changed",
    "permission.role.changed",
    "permission.knowledge_base.changed",
    "permission.document.changed",
    "temporary_grant.expired",
}

DOCUMENT_EVENTS = {
    "document.version.published",
    "document.offlined",
    "document.permission.changed",
    "document.paused",
}

QA_EVENTS = {
    "qa.published",
    "qa.invalidated",
}


class IdempotentCacheInvalidator:
    """重复事件不得造成重复副作用（幂等集合）。"""

    def __init__(self, cache: QueryAnswerCache | None = None):
        self.cache = cache or default_query_cache
        self._seen: set[str] = set()

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = event.get("event_id") or ""
        event_type = event.get("event_type") or ""
        tenant_id = event.get("tenant_id") or ""
        if not event_id or not event_type or not tenant_id:
            return {"ok": False, "reason": "invalid_event"}
        if event_id in self._seen:
            return {"ok": True, "idempotent": True, "invalidated": 0}
        self._seen.add(event_id)

        invalidated = 0
        if event_type in PERMISSION_EVENTS | DOCUMENT_EVENTS | QA_EVENTS:
            scope_hash = (event.get("payload") or {}).get("scope_hash")
            invalidated = self.cache.invalidate_scope(tenant_id, scope_hash)
            logger.info(
                "cache_invalidated",
                event_type=event_type,
                event_id=event_id,
                tenant_id=tenant_id,
                invalidated=invalidated,
            )
            return {"ok": True, "idempotent": False, "invalidated": invalidated}
        return {"ok": True, "ignored": True, "invalidated": 0}
