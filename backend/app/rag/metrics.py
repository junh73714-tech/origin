"""成员6 Prometheus 指标（命名可与成员7聚合对齐）。"""
from __future__ import annotations

try:
    from prometheus_client import Counter, Histogram
except Exception:  # noqa: BLE001
    Counter = None  # type: ignore[assignment,misc]
    Histogram = None  # type: ignore[assignment,misc]


if Counter is not None:
    RAG_QUERY_TOTAL = Counter(
        "rag_m6_query_total",
        "成员6 问答请求次数",
        ["answer_type", "cache_hit"],
    )
    RAG_PERMISSION_DENY_TOTAL = Counter(
        "rag_m6_permission_deny_total",
        "成员6 权限拒绝次数",
        ["resource"],
    )
    RAG_CACHE_EVENTS = Counter(
        "rag_m6_cache_events_total",
        "成员6 缓存命中/失效",
        ["event"],
    )
    RAG_STAGE_LATENCY = Histogram(
        "rag_m6_stage_latency_seconds",
        "成员6 阶段耗时",
        ["stage"],
        buckets=(0.01, 0.05, 0.1, 0.3, 1, 3, 10),
    )
else:
    RAG_QUERY_TOTAL = None
    RAG_PERMISSION_DENY_TOTAL = None
    RAG_CACHE_EVENTS = None
    RAG_STAGE_LATENCY = None


def observe_stage(stage: str, seconds: float) -> None:
    if RAG_STAGE_LATENCY is not None:
        RAG_STAGE_LATENCY.labels(stage=stage).observe(seconds)


def inc_query(answer_type: str, cache_hit: bool) -> None:
    if RAG_QUERY_TOTAL is not None:
        RAG_QUERY_TOTAL.labels(answer_type=answer_type or "unknown", cache_hit=str(cache_hit)).inc()


def inc_cache(event: str) -> None:
    if RAG_CACHE_EVENTS is not None:
        RAG_CACHE_EVENTS.labels(event=event).inc()


def inc_deny(resource: str) -> None:
    if RAG_PERMISSION_DENY_TOTAL is not None:
        RAG_PERMISSION_DENY_TOTAL.labels(resource=resource).inc()
