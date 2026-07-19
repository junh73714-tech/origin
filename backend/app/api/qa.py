"""
问答路由（成员6 + 成员7）。

成员6：聊天/SSE/会话/引用/调试检索与缓存失效（/api/v1/qa/* 联调契约）。
成员7：标准问答 CRUD、审核发布、候选问答、匹配与质量检查等生命周期管理。
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.cache.query.invalidation import IdempotentCacheInvalidator
from app.cache.query.keys import build_query_cache_key, digest_text
from app.cache.query.store import default_query_cache
from app.conversation.service import default_conversation_store
from app.conversation.sse import aiter_chat_sse, format_sse
from app.core.dependencies import DBSession, RequiredAccess
from app.core.logging import get_logger
from app.core.responses import paginated_response, success_response
from app.core.security import AccessContext
from app.models.qa import ReviewAction
from app.prompts.qa_system import PROMPT_VERSION
from app.providers.deterministic_embedding import get_embedding_provider
from app.providers.llm.provider import get_llm_provider
from app.providers.reranker.provider import get_reranker_provider
from app.rag.graph import QAGraph
from app.rag.metrics import inc_cache, inc_query
from app.rag.standard_qa_adapter import create_standard_qa_matcher
from app.retrieval.keyword import InMemoryKeywordIndex, KeywordRetriever
from app.retrieval.permission_adapter import DefaultPermissionAdapter, compute_scope_hash
from app.retrieval.service import HybridRetrievalService
from app.retrieval.vector import InMemoryVectorStore, VectorRetriever
from app.schemas.qa import (
    CandidateQAGenerateRequest,
    CandidateQAReviewRequest,
    CandidateQAResponse,
    QAMatchRequest,
    QAReviewRecordResponse,
    QAReviewSubmitRequest,
    StandardQACreate,
    StandardQADetailResponse,
    StandardQADisableRequest,
    StandardQAPublishRequest,
    StandardQAResponse,
    StandardQAUpdate,
)
from app.services.qa_matching_service import qa_matching_service
from app.services.qa_quality_service import qa_quality_check_service
from app.services.qa_service import qa_service

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
# USE_MEMBER7_STANDARD_QA=1 时走成员7桥接，否则 Mock
_graph = QAGraph(retrieval=_retrieval, standard_qa=create_standard_qa_matcher())
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
    """兼容旧调用：RequiredAccess 已在依赖里完成 PermissionService 富化。"""
    if not getattr(access, "scope_hash", None):
        access.scope_hash = compute_scope_hash(access)
    if not hasattr(access, "deny_document_ids") or access.deny_document_ids is None:
        access.deny_document_ids = []
    if not hasattr(access, "knowledge_base_ids") or access.knowledge_base_ids is None:
        access.knowledge_base_ids = list(
            (access.data_scopes or {}).get("knowledge_base", []) or []
        )
    if not hasattr(access, "max_confidentiality_level"):
        access.max_confidentiality_level = 0
    if not hasattr(access, "temporary_grants") or access.temporary_grants is None:
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


# ============================================================================
# 成员6：聊天 / 会话 / 调试
# ============================================================================

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
                refusal_reason=state.refusal_reason,
                evidence_status=state.evidence_status or None,
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


# ============================================================================
# 成员7：标准问答 CRUD
# ============================================================================

@router.post("/standard", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_standard_qa(
    data: StandardQACreate,
    db: DBSession,
    access: RequiredAccess,
):
    """创建标准问答（草稿状态）"""
    qa = await qa_service.create_qa(
        db=db,
        data=data.model_dump(),
        user_id=access.user_id,
        tenant_id=access.tenant_id,
    )
    return success_response(
        data={"id": qa.id, "status": qa.status},
        message="标准问答创建成功",
    )


@router.get("/standard")
async def list_standard_qas(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, description="搜索关键词"),
    status: str | None = Query(default=None, description="状态筛选"),
    category: str | None = Query(default=None, description="分类筛选"),
    knowledge_base_id: str | None = Query(default=None, description="知识库 ID 筛选"),
    is_machine_generated: bool | None = Query(default=None, description="是否机器生成"),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
):
    """查询标准问答列表"""
    items, total = await qa_service.list_qas(
        db=db,
        tenant_id=access.tenant_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        category=category,
        knowledge_base_id=knowledge_base_id,
        is_machine_generated=is_machine_generated,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_response(
        items=[StandardQAResponse.model_validate(item).model_dump() for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/standard/{qa_id}")
async def get_standard_qa(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """获取标准问答详情"""
    qa = await qa_service.get_qa_or_raise(db, qa_id, load_relations=True)
    return success_response(
        data=StandardQADetailResponse.model_validate(qa).model_dump(),
    )


@router.put("/standard/{qa_id}")
async def update_standard_qa(
    qa_id: str,
    data: StandardQAUpdate,
    db: DBSession,
    access: RequiredAccess,
):
    """更新标准问答"""
    qa = await qa_service.update_qa(
        db=db,
        qa_id=qa_id,
        data=data.model_dump(exclude_none=True),
        user_id=access.user_id,
    )
    return success_response(
        data=StandardQAResponse.model_validate(qa).model_dump(),
        message="标准问答更新成功",
    )


# ============================================================================
# 成员7：审核流程
# ============================================================================

@router.post("/standard/{qa_id}/submit-review")
async def submit_for_review(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """提交审核"""
    qa = await qa_service.submit_for_review(db, qa_id, access.user_id)
    return success_response(
        data={"id": qa.id, "status": qa.status},
        message="已提交审核",
    )


@router.post("/reviews")
async def submit_review(
    data: QAReviewSubmitRequest,
    db: DBSession,
    access: RequiredAccess,
):
    """提交审核结果"""
    from app.core.exceptions import ValidationError

    action = data.action
    qa_id = data.qa_id

    if action == ReviewAction.APPROVE:
        qa = await qa_service.approve_review(
            db, qa_id, access.user_id, data.comment, data.review_details
        )
    elif action == ReviewAction.REJECT:
        qa = await qa_service.reject_review(
            db, qa_id, access.user_id, data.comment, data.review_details
        )
    elif action == ReviewAction.RETURN_FOR_MODIFICATION:
        qa = await qa_service.return_for_modification(
            db, qa_id, access.user_id, data.comment
        )
    elif action == ReviewAction.PUBLISH:
        qa = await qa_service.publish_qa(db, qa_id, access.user_id)
    elif action == ReviewAction.DISABLE:
        qa = await qa_service.disable_qa(
            db, qa_id, access.user_id, data.comment or "手动停用"
        )
    elif action == ReviewAction.MARK_DUPLICATE:
        duplicate_of_id = (data.review_details or {}).get("duplicate_of_id", "")
        if not duplicate_of_id:
            raise ValidationError("标记重复时需要指定目标问答 ID")
        qa = await qa_service.mark_as_duplicate(
            db, qa_id, duplicate_of_id, access.user_id
        )
    elif action == ReviewAction.MARK_SOURCE_ISSUE:
        qa = await qa_service.disable_qa(
            db, qa_id, access.user_id, data.comment or "来源文档问题"
        )
    else:
        raise ValidationError(f"不支持的审核动作: {action}")

    return success_response(
        data={"id": qa.id, "status": qa.status},
        message=f"审核操作 '{action}' 执行成功",
    )


@router.get("/reviews")
async def list_review_records(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    qa_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    reviewer_id: str | None = Query(default=None),
    sort_by: str = Query(default="review_time"),
    sort_order: str = Query(default="desc"),
):
    """查询审核记录"""
    items, total = await qa_service.list_review_records(
        db=db,
        tenant_id=access.tenant_id,
        page=page,
        page_size=page_size,
        qa_id=qa_id,
        action=action,
        reviewer_id=reviewer_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_response(
        items=[QAReviewRecordResponse.model_validate(item).model_dump() for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# 成员7：发布与停用
# ============================================================================

@router.post("/standard/{qa_id}/publish")
async def publish_standard_qa(
    qa_id: str,
    data: StandardQAPublishRequest | None = None,
    db: DBSession = Depends(),
    access: RequiredAccess = Depends(),
):
    """发布标准问答"""
    qa = await qa_service.publish_qa(
        db=db,
        qa_id=qa_id,
        user_id=access.user_id,
        effective_start=data.effective_start if data else None,
        effective_end=data.effective_end if data else None,
    )
    return success_response(
        data={"id": qa.id, "status": qa.status, "published_at": qa.published_at.isoformat() if qa.published_at else None},
        message="标准问答已发布",
    )


@router.post("/standard/{qa_id}/disable")
async def disable_standard_qa(
    qa_id: str,
    data: StandardQADisableRequest,
    db: DBSession,
    access: RequiredAccess,
):
    """停用标准问答"""
    qa = await qa_service.disable_qa(
        db=db,
        qa_id=qa_id,
        user_id=access.user_id,
        reason=data.reason,
    )
    return success_response(
        data={"id": qa.id, "status": qa.status},
        message="标准问答已停用",
    )


# ============================================================================
# 成员7：候选问答
# ============================================================================

@router.post("/candidates/generate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_candidate_generation(
    data: CandidateQAGenerateRequest,
    background_tasks: BackgroundTasks,
    access: RequiredAccess,
):
    """触发候选问答生成任务（异步）"""
    from app.tasks.qa_tasks import generate_candidate_qas

    # 使用 BackgroundTasks 异步执行
    background_tasks.add_task(
        generate_candidate_qas,
        knowledge_base_id=data.knowledge_base_id,
        document_ids=data.document_ids,
        chunk_ids=data.chunk_ids,
        max_candidates=data.max_candidates,
        model=data.model,
        prompt_version=data.prompt_version,
        user_id=access.user_id,
        tenant_id=access.tenant_id,
    )

    return success_response(
        data={
            "knowledge_base_id": data.knowledge_base_id,
            "status": "processing",
        },
        message="候选问答生成任务已触发",
    )


@router.get("/candidates")
async def list_candidates(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    knowledge_base_id: str | None = Query(default=None),
    source: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
):
    """查询候选问答列表"""
    items, total = await qa_service.list_candidates(
        db=db,
        tenant_id=access.tenant_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        knowledge_base_id=knowledge_base_id,
        source=source,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_response(
        items=[CandidateQAResponse.model_validate(item).model_dump() for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/candidates/{candidate_id}/review")
async def review_candidate(
    candidate_id: str,
    data: CandidateQAReviewRequest,
    db: DBSession,
    access: RequiredAccess,
):
    """审核候选问答"""
    from app.core.exceptions import ValidationError

    action = data.action

    if action == "approve":
        candidate = await qa_service.approve_candidate(
            db, candidate_id, access.user_id, data.comment
        )
        message = "候选问答审核通过"
    elif action == "reject":
        candidate = await qa_service.reject_candidate(
            db, candidate_id, access.user_id, data.comment
        )
        message = "候选问答已驳回"
    elif action == "mark_duplicate":
        candidate = await qa_service.reject_candidate(
            db, candidate_id, access.user_id,
            f"标记为重复: {data.duplicate_of_standard_id or ''}"
        )
        message = "候选问答已标记为重复"
    else:
        raise ValidationError(f"不支持的审核动作: {action}")

    return success_response(
        data={"id": candidate.id, "status": candidate.status},
        message=message,
    )


@router.post("/candidates/{candidate_id}/convert")
async def convert_candidate_to_standard(
    candidate_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """将候选问答转为标准问答"""
    qa = await qa_service.convert_candidate_to_standard(
        db, candidate_id, access.user_id
    )
    return success_response(
        data={"id": qa.id, "status": qa.status, "question": qa.question},
        message="候选问答已转为标准问答",
    )


# ============================================================================
# 成员7：标准问答匹配（供成员6调用）
# ============================================================================

@router.post("/match")
async def match_standard_qa(
    data: QAMatchRequest,
    db: DBSession,
):
    """
    标准问答匹配接口
    供成员6的正式问答链路调用，在执行 RAG 检索前先匹配标准问答
    """
    result = await qa_matching_service.match(
        db=db,
        query=data.query,
        keywords=data.keywords,
        entities=data.entities,
        intent=data.intent,
        access_context=data.access_context,
        knowledge_base_ids=data.knowledge_base_ids,
        top_k=data.top_k,
        threshold=data.threshold,
        trusted_threshold=data.trusted_threshold,
    )

    return success_response(data=result)


# ============================================================================
# 成员7：质量检查
# ============================================================================

@router.post("/standard/{qa_id}/quality-check")
async def run_quality_check(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
    background_tasks: BackgroundTasks,
):
    """触发质量检查"""
    from app.tasks.qa_tasks import run_quality_checks

    background_tasks.add_task(run_quality_checks, qa_id=qa_id)

    return success_response(
        data={"qa_id": qa_id, "status": "processing"},
        message="质量检查任务已触发",
    )


@router.get("/standard/{qa_id}/quality-check")
async def get_quality_check_result(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """获取质量检查结果"""
    summary = await qa_quality_check_service.get_check_summary(db, qa_id)
    return success_response(data=summary)


# ============================================================================
# 成员7：文档版本联动（内部接口）
# ============================================================================

@router.post("/internal/document-change")
async def handle_document_change(
    event_type: str = Query(..., description="事件类型"),
    document_id: str = Query(..., description="文档 ID"),
    new_version: int = Query(default=1, description="新版本号"),
    db: DBSession = Depends(),
):
    """
    处理文档版本变更（内部接口）
    由 Outbox 事件消费者或文档服务调用
    """
    from app.services.outbox_consumer import outbox_event_consumer

    result = await outbox_event_consumer.handle_single_event(
        db=db,
        event_type=event_type,
        document_id=document_id,
        new_version=new_version,
    )
    return success_response(data=result, message="文档变更已处理")


# ============================================================================
# 成员7：状态流转查询
# ============================================================================

@router.get("/standard/{qa_id}/allowed-transitions")
async def get_allowed_transitions(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """获取当前状态允许的流转目标"""
    qa = await qa_service.get_qa_or_raise(db, qa_id)
    allowed = qa_service.get_allowed_transitions(qa.status)
    return success_response(
        data={
            "qa_id": qa_id,
            "current_status": qa.status,
            "allowed_transitions": allowed,
        }
    )
