"""内存查询缓存（可替换为 Redis）。按 tenant + scope_hash 隔离。"""
from __future__ import annotations

import time
from typing import Any


class QueryAnswerCache:
    """简单进程内缓存，键必须包含 scope_hash。"""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> dict[str, Any] | None:
        item = self._store.get(key)
        if not item:
            self.misses += 1
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._store.pop(key, None)
            self.misses += 1
            return None
        # 反序列化失败保护：结构校验
        if not isinstance(value, dict) or "answer" not in value:
            self._store.pop(key, None)
            self.misses += 1
            return None
        self.hits += 1
        return value

    def set(self, key: str, value: dict[str, Any]) -> None:
        # 约定键格式：qa_cache:{tenant_id}:{scope_hash}:{digest}
        parts = key.split(":")
        if len(parts) < 4 or parts[0] != "qa_cache" or not parts[2]:
            raise ValueError("缓存键必须包含 tenant 与 scope_hash 分段")
        self._store[key] = (time.time() + self.ttl_seconds, value)

    def invalidate_prefix(self, prefix: str) -> int:
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            self._store.pop(k, None)
        return len(keys)

    def invalidate_scope(self, tenant_id: str, scope_hash: str | None = None) -> int:
        if scope_hash:
            prefix = f"qa_cache:{tenant_id}:{scope_hash}:"
        else:
            prefix = f"qa_cache:{tenant_id}:"
        return self.invalidate_prefix(prefix)

    def clear(self) -> None:
        self._store.clear()


# 进程级默认缓存
default_query_cache = QueryAnswerCache()
