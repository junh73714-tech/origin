"""缓存隔离与 SSE 序列测试。"""
from app.cache.query.invalidation import IdempotentCacheInvalidator
from app.cache.query.keys import build_query_cache_key, digest_text
from app.cache.query.store import QueryAnswerCache
from app.conversation.sse import iter_chat_sse


def test_cache_key_requires_scope_isolation():
    k1 = build_query_cache_key(
        tenant_id="t1",
        scope_hash="scope_a",
        knowledge_base_ids=["kb1"],
        document_version_digest="v1",
        standard_qa_version="q1",
        question_digest=digest_text("同一问题"),
        llm_version="m1",
        embedding_version="e1",
        reranker_version="r1",
        prompt_version="p1",
    )
    k2 = build_query_cache_key(
        tenant_id="t1",
        scope_hash="scope_b",
        knowledge_base_ids=["kb1"],
        document_version_digest="v1",
        standard_qa_version="q1",
        question_digest=digest_text("同一问题"),
        llm_version="m1",
        embedding_version="e1",
        reranker_version="r1",
        prompt_version="p1",
    )
    assert k1 != k2
    cache = QueryAnswerCache()
    cache.set(k1, {"answer": "A", "scope_hash": "scope_a"})
    assert cache.get(k1)["answer"] == "A"
    assert cache.get(k2) is None


def test_event_idempotent_invalidation():
    cache = QueryAnswerCache()
    key = build_query_cache_key(
        tenant_id="t1",
        scope_hash="s1",
        knowledge_base_ids=[],
        document_version_digest="x",
        standard_qa_version="x",
        question_digest="q",
        llm_version="l",
        embedding_version="e",
        reranker_version="r",
        prompt_version="p",
    )
    cache.set(key, {"answer": "cached"})
    inv = IdempotentCacheInvalidator(cache)
    event = {
        "event_id": "evt_1",
        "event_type": "permission.user.changed",
        "tenant_id": "t1",
        "payload": {"scope_hash": "s1"},
    }
    r1 = inv.handle_event(event)
    r2 = inv.handle_event(event)
    assert r1["invalidated"] >= 1
    assert r2["idempotent"] is True
    assert cache.get(key) is None


def test_sse_event_sequence():
    events = list(
        iter_chat_sse(
            answer="你好世界",
            references=[{"citation_id": "cit_1"}],
            conversation_id="cnv_1",
            message_id="msg_1",
            trace_id="tr_1",
            chunk_size=2,
        )
    )
    joined = "".join(events)
    assert "event: message_start" in joined
    assert "event: message" in joined
    assert "event: answer_delta" in joined
    assert "event: citation" in joined
    assert "event: metadata" in joined
    assert "event: done" in joined
    assert "cnv_1" in joined and "msg_1" in joined
