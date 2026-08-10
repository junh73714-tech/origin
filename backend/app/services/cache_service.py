"""
成员4：权限缓存服务
实现权限缓存、失效机制和Outbox事件处理
"""
import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

PERMISSION_CACHE_PREFIX = "permission:user:"
ACCESS_CONTEXT_CACHE_PREFIX = "access_context:"
SCOPE_HASH_CACHE_PREFIX = "scope_hash:"

redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """获取Redis客户端"""
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis.url, decode_responses=True)
    return redis_client


async def get_permission_cache(user_id: str) -> dict[str, Any] | None:
    """获取用户权限缓存"""
    client = get_redis_client()
    key = f"{PERMISSION_CACHE_PREFIX}{user_id}"
    data = await client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_permission_cache(user_id: str, data: dict[str, Any], ttl_seconds: int = 3600) -> None:
    """设置用户权限缓存"""
    client = get_redis_client()
    key = f"{PERMISSION_CACHE_PREFIX}{user_id}"
    await client.setex(key, ttl_seconds, json.dumps(data))
    logger.debug("permission_cache_set", user_id=user_id)


async def invalidate_permission_cache(user_id: str) -> None:
    """失效用户权限缓存"""
    client = get_redis_client()
    keys = [
        f"{PERMISSION_CACHE_PREFIX}{user_id}",
        f"{ACCESS_CONTEXT_CACHE_PREFIX}{user_id}",
        f"{SCOPE_HASH_CACHE_PREFIX}{user_id}",
    ]
    await client.delete(*keys)
    logger.info("permission_cache_invalidated", user_id=user_id)


async def get_access_context_cache(user_id: str) -> dict[str, Any] | None:
    """获取用户访问上下文缓存"""
    client = get_redis_client()
    key = f"{ACCESS_CONTEXT_CACHE_PREFIX}{user_id}"
    data = await client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_access_context_cache(user_id: str, data: dict[str, Any], ttl_seconds: int = 1800) -> None:
    """设置用户访问上下文缓存"""
    client = get_redis_client()
    key = f"{ACCESS_CONTEXT_CACHE_PREFIX}{user_id}"
    await client.setex(key, ttl_seconds, json.dumps(data))
    logger.debug("access_context_cache_set", user_id=user_id)


async def get_scope_hash(user_id: str) -> str | None:
    """获取用户权限范围哈希"""
    client = get_redis_client()
    key = f"{SCOPE_HASH_CACHE_PREFIX}{user_id}"
    return await client.get(key)


async def set_scope_hash(user_id: str, scope_hash: str, ttl_seconds: int = 1800) -> None:
    """设置用户权限范围哈希"""
    client = get_redis_client()
    key = f"{SCOPE_HASH_CACHE_PREFIX}{user_id}"
    await client.setex(key, ttl_seconds, scope_hash)
    logger.debug("scope_hash_set", user_id=user_id)


async def invalidate_user_cache(user_id: str) -> None:
    """失效用户所有相关缓存"""
    await invalidate_permission_cache(user_id)


async def publish_permission_change_event(user_id: str, event_type: str, details: dict[str, Any]) -> None:
    """发布权限变更事件到Redis Pub/Sub"""
    client = get_redis_client()
    channel = "permission_change"
    event = {
        "user_id": user_id,
        "event_type": event_type,
        "details": details,
    }
    await client.publish(channel, json.dumps(event))
    logger.info("permission_change_event_published", user_id=user_id, event_type=event_type)


async def publish_temporary_grant_expired_event(grant_id: str, user_id: str) -> None:
    """发布临时授权过期事件"""
    client = get_redis_client()
    channel = "temporary_grant_expired"
    event = {
        "grant_id": grant_id,
        "user_id": user_id,
    }
    await client.publish(channel, json.dumps(event))
    logger.info("temporary_grant_expired_event_published", grant_id=grant_id, user_id=user_id)