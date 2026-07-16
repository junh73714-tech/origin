"""
问答路由（成员6）。
冻结契约路径：/api/v1/qa/*
标准问答 CRUD 由成员7主责，此处仅提供只读列表占位与联调适配，避免双轨写冲突。
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.cache.query.invalidation import IdempotentCacheInvalidator
from app.cache.query.keys import build_query_cache_key, digest_text
from app.cache.query.store import default_query_cache
from app.conversation.service import default_conversation_store
from app.conversation.sse import aiter_chat_sse, format_sse
from app.core.dependencies import RequiredAccess
from app.core.logging import get_logger
from app.core.responses import paginated_response, success_response
from app.core.security import AccessContext
from app.prompts.qa_system import PROMPT_VERSION
from app.providers.embedding.provider import get_embedding_provider
from app.providers.llm.provider import get_llm_provider
from app.providers.reranker.provider import get_reranker_provider
from app.rag.graph import QAGraph
from app.rag.metrics import inc_cache, inc_query
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever

logger = get_logger(__name__)

router = APIRouter()
qa_router = router  # 供 main.py 导入，公共变更标记成员1评审

# 演示用空索引；集成时替换为真实 OpenSearch/pgvector
_demo_keyword = KeywordRetriever(client=InMemoryKeywordIndex([]))
_demo_vector = VectorRetriever(
    embedding_provider=get_embedding_provider(),
    store=InMemoryVectorStore([]),
)
_retrieval = HybridRetrievalService(_demo_keyword, _demo_vector)
_graph = QAGraph(retrieval=_retrieval)
_invalidator = IdempotentCacheInvalidator(default_query_cache)
_permission = DefaultPermissionAdapter()


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    content: str = Field(..., min_length=1)


class CancelRequest(BaseModel):
    reason: str | None = None


class DebugQueryRequest(BaseModel):
    content: str = Field(..., min_length=1)
    knowledge_base_ids: list[str] = Field(default_factory=list)


def _enrich_access(access: AccessContext) -> AccessContext:
    if not getattr(access, "scope_hash", None):
        access.scope_hash = compute_scope_hash(access)
    if not hasattr(access, "deny_document_ids"):
        access.deny_document_ids = []
    if not hasattr(access, "knowledge_base_ids"):
        access.knowledge_base_ids = list(
            (access.data_scopes or {}).get("knowledge_base", []) or []
        )
    if not hasattr(access, "max_confidentiality_level"):
        access.max_confidentiality_level = 0
    if not hasattr(access, "temporary_grants"):
        access.temporary_grants = []
    return access


def _build_cache_key(access: AccessContext, content: str) -> tuple[str, str]:
    emb = get_embedding_provider()
    llm = get_llm_provider()
    rerank = get_reranker_provider()
    scope_hash = getattr(access, "scope_hash", "") or compute_scope_hash(access)
    key = build_query_cache_key(
        tenant_id=access.tenant_id,
        scope_hash=scope_hash,
        knowledge_base_ids=list(getattr(access, "knowledge_base_ids", []) or []),
        document_version_digest="none",
        standard_qa_version="none",
        question_digest=digest_text(content),
        llm_version=f"{llm.model_name}:mock",
        embedding_version=f"{emb.model_name}:{emb.model_version}:{emb.dimension}",
        reranker_version=f"{rerank.model_name}:mock",
        prompt_version=PROMPT_VERSION,
    )
    return key, scope_hash


@router.post("/chat")
async def chat(
    body: ChatRequest,
    access: RequiredAccess,
    request: Request,
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
):
    """发送消息，SSE 流式返回。"""
    access = _enrich_access(access)
    trace_id = getattr(request.state, "trace_id", None) or f"tr_{uuid.uuid4().hex[:12]}"
    request_id = x_request_id or getattr(request.state, "request_id", None)
    cache_key, scope_hash = _build_cache_key(access, body.content)
    cached = default_query_cache.get(cache_key)

    started = default_conversation_store.begin_query(
        tenant_id=access.tenant_id,
        user_id=access.user_id,
        conversation_id=body.conversation_id,
        original_query=body.content,
        scope_hash=scope_hash,
        trace_id=trace_id,
        request_id=request_id,
    )
    query_id = started["query_id"]
    conversation_id = started["conversation_id"]

    async def event_stream():
        try:
            if cached:
                inc_cache("hit")
                ids = default_conversation_store.append_cached_turn(
                    conversation_id=conversation_id,
                    tenant_id=access.tenant_id,
                    user_id=access.user_id,
                    user_content=body.content,
                    cached=cached,
                    trace_id=trace_id,
                    scope_hash=scope_hash,
                    query_id=query_id,
                )
                inc_query(cached.get("answer_type", "rag"), True)
                async for chunk in aiter_chat_sse(
                    answer=cached.get("answer", ""),
                    references=cached.get("citations", []),
                    conversation_id=ids["conversation_id"],
                    message_id=ids["message_id"],
                    trace_id=trace_id,
                    answer_type=cached.get("answer_type", "rag"),
                    metadata={"cache_hit": True, "request_id": request_id, "query_id": query_id},
                    query_id=query_id,
                ):
                    yield chunk
                return

            inc_cache("miss")
            history = default_conversation_store.history_texts(conversation_id, access.user_id)
            state = _graph.run(
                body.content,
                access,
                conversation_id=conversation_id,
                trace_id=trace_id,
                history=history,
                cancel_check=lambda: default_conversation_store.is_cancelled(query_id),
            )
            ids = default_conversation_store.append_turn(
                conversation_id=conversation_id,
                tenant_id=access.tenant_id,
                user_id=access.user_id,
                user_content=body.content,
                state=state,
                query_id=query_id,
                cache_hit=False,
            )
            if not state.cancelled:
                default_query_cache.set(
                    cache_key,
                    {
                        "answer": state.generated_answer,
                        "citations": state.citations,
                        "answer_type": state.answer_type,
                        "scope_hash": scope_hash,
                    },
                )
            inc_query(state.answer_type or "rag", False)
            async for chunk in aiter_chat_sse(
                answer=state.generated_answer,
                references=state.citations,
                conversation_id=ids["conversation_id"],
                message_id=ids["message_id"],
                trace_id=trace_id,
                answer_type=state.answer_type or "rag",
                metadata={
                    "cache_hit": False,
                    "request_id": request_id,
                    "timings_ms": state.timings_ms,
                    "refusal_reason": state.refusal_reason,
                    "query_id": query_id,
                    "cancelled": state.cancelled,
                },
                query_id=query_id,
            ):
                yield chunk
        except Exception as exc:  # noqa: BLE001
            logger.error("chat_stream_error", error=str(exc), trace_id=trace_id)
            yield format_sse(
                "error",
                {"message": "问答处理失败", "code": "BIZ_RETRIEVAL_FAILED", "query_id": query_id},
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations")
async def list_conversations(access: RequiredAccess):
    access = _enrich_access(access)
    items = default_conversation_store.list_conversations(access.user_id, access.tenant_id)
    return paginated_response(items=items, total=len(items), page=1, page_size=20)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, access: RequiredAccess):
    access = _enrich_access(access)
    row = default_conversation_store.get_conversation(conversation_id, access.user_id)
    if not row:
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("conversation", conversation_id)
    return success_response(data=row)


@router.get("/citations/{citation_id}")
async def get_citation(citation_id: str, access: RequiredAccess):
    """按 citation_id 查询，不暴露 MinIO 真实地址。"""
    access = _enrich_access(access)
    cit = default_conversation_store.get_citation(citation_id)
    if not cit:
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("citation", citation_id)
    if not _permission.can_open_citation(access, cit):
        from app.core.exceptions import AuthorizationError

        raise AuthorizationError(message="无权打开该引用", details={"citation_id": citation_id})
    safe = {
        "citation_id": cit.get("citation_id"),
        "document_name": cit.get("document_name"),
        "document_version": cit.get("document_version") or cit.get("document_version_id"),
        "title_path": cit.get("title_path"),
        "page_start": cit.get("page_start"),
        "page_end": cit.get("page_end"),
        "quote": cit.get("quote") or cit.get("quote_text"),
        "source_status": cit.get("source_status") or cit.get("status"),
    }
    return success_response(data=safe)


@router.post("/queries/{query_id}/cancel")
async def cancel_query(query_id: str, body: CancelRequest, access: RequiredAccess):
    del body
    access = _enrich_access(access)
    ok = default_conversation_store.cancel_query(query_id, access.user_id, access.tenant_id)
    if not ok:
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("query", query_id)
    return success_response(data={"query_id": query_id, "cancelled": True})


@router.get("/queries/{query_id}/stream")
async def stream_query(query_id: str, access: RequiredAccess):
    """按 query_id 重放最终结果（契约扩展，供成员2重连）。"""
    access = _enrich_access(access)
    q = default_conversation_store.get_query(query_id)
    if not q or q.get("user_id") != access.user_id:
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("query", query_id)
    state = q.get("state") or {}

    async def event_stream():
        async for chunk in aiter_chat_sse(
            answer=state.get("generated_answer") or "",
            references=state.get("citations") or [],
            conversation_id=q.get("conversation_id") or "",
            message_id=q.get("message_id") or "",
            trace_id=state.get("trace_id") or "",
            answer_type=state.get("answer_type") or "rag",
            metadata={"replay": True, "query_id": query_id},
            query_id=query_id,
        ):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/messages/{message_id}/regenerate")
async def regenerate_message(message_id: str, access: RequiredAccess, request: Request):
    """重新生成助手消息。"""
    access = _enrich_access(access)
    msg = default_conversation_store.get_message(message_id)
    if not msg or msg.get("role") != "assistant":
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("message", message_id)
    conv = default_conversation_store.get_conversation(msg["conversation_id"], access.user_id)
    if not conv:
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("conversation", msg["conversation_id"])
    # 取上一条用户消息
    user_content = ""
    for m in reversed(conv.get("messages") or []):
        if m.get("role") == "user":
            user_content = m.get("content") or ""
            break
    if not user_content:
        from app.core.exceptions import ValidationError

        raise ValidationError(message="找不到可重生成的用户问题")

    trace_id = getattr(request.state, "trace_id", None) or f"tr_{uuid.uuid4().hex[:12]}"
    history = default_conversation_store.history_texts(conv["id"], access.user_id)
    started = default_conversation_store.begin_query(
        tenant_id=access.tenant_id,
        user_id=access.user_id,
        conversation_id=conv["id"],
        original_query=user_content,
        scope_hash=getattr(access, "scope_hash", "") or compute_scope_hash(access),
        trace_id=trace_id,
    )
    query_id = started["query_id"]
    state = _graph.run(
        user_content,
        access,
        conversation_id=conv["id"],
        trace_id=trace_id,
        history=history,
        cancel_check=lambda: default_conversation_store.is_cancelled(query_id),
    )
    ids = default_conversation_store.append_turn(
        conversation_id=conv["id"],
        tenant_id=access.tenant_id,
        user_id=access.user_id,
        user_content=user_content,
        state=state,
        query_id=query_id,
    )
    return success_response(
        data={
            "conversation_id": ids["conversation_id"],
            "message_id": ids["message_id"],
            "query_id": query_id,
            "answer": state.generated_answer,
            "answer_type": state.answer_type,
            "citations": state.citations,
        }
    )


@router.post("/debug/query")
async def debug_query(body: DebugQueryRequest, access: RequiredAccess):
    """检索调试接口（成员3后台联调）。"""
    access = _enrich_access(access)
    if not (
        access.has_permission("system.configure")
        or access.has_permission("audit.read")
        or access.is_super_admin()
        or access.has_permission("*")
    ):
        from app.core.exceptions import AuthorizationError

        raise AuthorizationError(message="需要调试权限")

    if body.knowledge_base_ids:
        access.knowledge_base_ids = body.knowledge_base_ids
        access.data_scopes = {
            **(access.data_scopes or {}),
            "knowledge_base": body.knowledge_base_ids,
        }
        access.scope_hash = compute_scope_hash(access)

    state = _graph.run(body.content, access, trace_id=f"dbg_{uuid.uuid4().hex[:10]}")
    safe_ctx = []
    for snip in state.selected_context:
        safe_ctx.append(
            {
                "citation_id": snip.get("citation_id"),
                "document_id": snip.get("document_id"),
                "chunk_id": snip.get("chunk_id"),
                "title_path": snip.get("title_path"),
                "status": snip.get("status"),
                "quote_preview": (snip.get("quote") or "")[:80],
            }
        )
    return success_response(
        data={
            "original_query": state.original_query,
            "rewritten_query": state.rewritten_query,
            "intent": state.intent,
            "keywords": state.keywords,
            "entities": state.entities,
            "permission_filter_summary": {
                "scope_hash": state.access_context.get("scope_hash"),
                "deny_document_ids": state.access_context.get("deny_document_ids"),
                "knowledge_base_ids": state.access_context.get("knowledge_base_ids"),
            },
            "standard_qa_match": state.standard_qa_result,
            "keyword_results": [x.get("chunk_id") for x in state.keyword_results],
            "vector_results": [x.get("chunk_id") for x in state.vector_results],
            "rrf_results": [x.get("chunk_id") for x in state.fused_results],
            "reranker_results": [x.get("chunk_id") for x in state.reranked_results],
            "final_context": safe_ctx,
            "evidence_score": state.evidence_score,
            "evidence_status": state.evidence_status,
            "answer": state.generated_answer,
            "citations": state.citations,
            "refusal_reason": state.refusal_reason,
            "timings_ms": state.timings_ms,
            "trace_id": state.trace_id,
            "debug": state.debug,
        }
    )


@router.post("/cache/invalidate-event")
async def invalidate_by_event(event: dict[str, Any], access: RequiredAccess):
    """供 Outbox 消费联调：幂等失效缓存。"""
    if not (access.has_permission("system.configure") or access.is_super_admin()):
        from app.core.exceptions import AuthorizationError

        raise AuthorizationError(message="需要系统配置权限")
    result = _invalidator.handle_event(event)
    if result.get("invalidated"):
        inc_cache("invalidate")
    return success_response(data=result)


@router.get("/standard")
async def list_standard_qa(
    access: RequiredAccess,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    category: str | None = None,
):
    del access, status, category
    return paginated_response(items=[], total=0, page=page, page_size=page_size)
