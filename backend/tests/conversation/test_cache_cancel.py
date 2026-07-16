"""会话缓存命中与取消测试。"""
from app.conversation.service import InMemoryConversationStore
from app.conversation.sse import iter_chat_sse
from app.core.security import AccessContext
from app.rag.state import RAGState
from app.retrieval.permission_adapter import compute_scope_hash


def test_cache_hit_path_does_not_need_graph_state():
    store = InMemoryConversationStore()
    started = store.begin_query(
        tenant_id="t1",
        user_id="u1",
        conversation_id=None,
        original_query="问题",
        scope_hash="s1",
        trace_id="tr1",
    )
    ids = store.append_cached_turn(
        conversation_id=started["conversation_id"],
        tenant_id="t1",
        user_id="u1",
        user_content="问题",
        cached={"answer": "缓存答案", "citations": [], "answer_type": "rag"},
        trace_id="tr1",
        scope_hash="s1",
        query_id=started["query_id"],
    )
    msg = store.get_message(ids["message_id"])
    assert msg["content"] == "缓存答案"
    assert store.query_logs[started["query_id"]]["cache_hit"] is True


def test_cancel_requires_owner():
    store = InMemoryConversationStore()
    started = store.begin_query(
        tenant_id="t1",
        user_id="u1",
        conversation_id=None,
        original_query="q",
        scope_hash="s",
        trace_id="t",
    )
    assert store.cancel_query(started["query_id"], "u2", "t1") is False
    assert store.cancel_query(started["query_id"], "u1", "t1") is True
    assert store.is_cancelled(started["query_id"]) is True


def test_sse_includes_query_id():
    events = "".join(
        iter_chat_sse(
            answer="hi",
            references=[],
            conversation_id="c1",
            message_id="m1",
            query_id="qry_1",
            chunk_size=10,
        )
    )
    assert "qry_1" in events
    assert "event: done" in events


def test_append_turn_writes_retrieval_logs():
    store = InMemoryConversationStore()
    access = AccessContext(user_id="u1", tenant_id="t1", roles=[], permissions=[])
    access.scope_hash = compute_scope_hash(access)
    state = RAGState(
        user_id="u1",
        tenant_id="t1",
        generated_answer="a",
        answer_type="rag",
        keyword_results=[{"chunk_id": "c1"}],
        fused_results=[{"chunk_id": "c1"}],
        access_context=access.to_dict(),
        timings_ms={"retrieval": 12},
    )
    ids = store.append_turn(
        conversation_id=None,
        tenant_id="t1",
        user_id="u1",
        user_content="q",
        state=state,
    )
    assert ids["query_id"]
    assert any(r["stage"] == "keyword" for r in store.retrieval_logs)
