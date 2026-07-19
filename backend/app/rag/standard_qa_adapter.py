"""
成员7标准问答匹配适配器。

只通过服务接口调用，不直接查询底层表/索引。
成员7未就绪时使用契约一致的测试替身。
正式对接：Member7StandardQABridge 将 QAMatchingService 的
{matched, results:[...]} 映射为本协议的单条 StandardQAMatchResult。
"""
from __future__ import annotations

import asyncio
import inspect
import os
from typing import Any, Callable, Protocol

from pydantic import BaseModel, Field


class StandardQAMatchResult(BaseModel):
    matched: bool = False
    qa_id: str = ""
    answer: str = ""
    variants: list[str] = Field(default_factory=list)
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    entity_consistency: float = 0.0
    scope_consistency: float = 0.0
    final_score: float = 0.0
    citations: list[dict[str, Any]] = Field(default_factory=list)
    status: str = ""
    reason: str = ""
    source_document_ids: list[str] = Field(default_factory=list)
    knowledge_base_id: str = ""
    trusted: bool = False


class StandardQAMatcher(Protocol):
    def match(
        self,
        question: str,
        keywords: list[str],
        entities: list[str],
        intent: str,
        access_context: dict[str, Any],
        knowledge_base_ids: list[str],
    ) -> StandardQAMatchResult: ...


def map_member7_item_to_result(item: dict[str, Any] | None, *, matched_flag: bool = True) -> StandardQAMatchResult:
    """将成员7单条 QAMatchResult（dict）映射为成员6协议对象。"""
    if not item:
        return StandardQAMatchResult(matched=False, reason="未命中标准问答")
    citations = list(item.get("citations") or [])
    # 兼容成员7 citation 仍可能带整型 document_version 的过渡期
    normalized_citations: list[dict[str, Any]] = []
    for cit in citations:
        if not isinstance(cit, dict):
            continue
        c = dict(cit)
        if "document_version_id" not in c and "document_version" in c:
            c["document_version_id"] = c.get("document_version")
        normalized_citations.append(c)
    return StandardQAMatchResult(
        matched=bool(item.get("matched", matched_flag)),
        trusted=bool(item.get("trusted", False)),
        qa_id=str(item.get("qa_id") or ""),
        answer=str(item.get("answer") or ""),
        variants=list(item.get("variants") or []),
        semantic_score=float(item.get("semantic_score") or 0.0),
        keyword_score=float(item.get("keyword_score") or 0.0),
        entity_consistency=float(item.get("entity_consistency") or 0.0),
        scope_consistency=float(item.get("scope_consistency") or 0.0),
        final_score=float(item.get("final_score") or 0.0),
        citations=normalized_citations,
        status=str(item.get("status") or ""),
        reason=str(item.get("reason") or ""),
        source_document_ids=[str(x) for x in (item.get("source_document_ids") or [])],
        knowledge_base_id=str(item.get("knowledge_base_id") or ""),
    )


def map_member7_response(response: dict[str, Any] | None) -> StandardQAMatchResult:
    """取 results[0] 映射；无结果则 matched=False。"""
    if not response:
        return StandardQAMatchResult(matched=False, reason="未命中标准问答")
    results = list(response.get("results") or [])
    if not results:
        return StandardQAMatchResult(
            matched=bool(response.get("matched", False)),
            reason=str(response.get("reason") or "未命中标准问答"),
        )
    return map_member7_item_to_result(results[0], matched_flag=bool(response.get("matched", True)))


def _run_maybe_async(coro_or_value: Any) -> Any:
    """在同步协议内执行可能为协程的成员7调用。"""
    if not inspect.isawaitable(coro_or_value):
        return coro_or_value
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        # 已在事件循环中：用独立线程跑，避免嵌套 deadlock
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro_or_value).result()
    return asyncio.run(coro_or_value)


class Member7StandardQABridge:
    """
    成员7桥接：把 QAMatchingService.match 的返回结构适配为 StandardQAMatcher。

    service.match 可为 sync 或 async；参数兼容 query= / question=。
    可选 db_provider：每次 match 时注入 AsyncSession（成员7正式服务需要）。
    """

    def __init__(
        self,
        service: Any,
        *,
        db_provider: Callable[[], Any] | None = None,
        threshold: float = 0.70,
        trusted_threshold: float = 0.85,
        top_k: int = 5,
    ):
        self.service = service
        self.db_provider = db_provider
        self.threshold = threshold
        self.trusted_threshold = trusted_threshold
        self.top_k = top_k

    def match(
        self,
        question: str,
        keywords: list[str],
        entities: list[str],
        intent: str,
        access_context: dict[str, Any],
        knowledge_base_ids: list[str],
    ) -> StandardQAMatchResult:
        kwargs: dict[str, Any] = {
            "query": question,
            "keywords": keywords,
            "entities": entities,
            "intent": intent,
            "access_context": access_context,
            "knowledge_base_ids": knowledge_base_ids,
            "top_k": self.top_k,
            "threshold": self.threshold,
            "trusted_threshold": self.trusted_threshold,
        }
        # 兼容仅接受 question= 的替身
        call = getattr(self.service, "match")
        try:
            sig = inspect.signature(call)
            params = sig.parameters
        except (TypeError, ValueError):
            params = {}

        if "query" not in params and "question" in params:
            kwargs.pop("query", None)
            kwargs["question"] = question
        if "db" in params:
            if self.db_provider is None:
                return StandardQAMatchResult(matched=False, reason="成员7匹配服务需要 db 会话")
            kwargs["db"] = self.db_provider()
        # 去掉服务端不认识的多余参数
        if params:
            kwargs = {k: v for k, v in kwargs.items() if k in params or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
            )}

        raw = _run_maybe_async(call(**kwargs))
        if isinstance(raw, StandardQAMatchResult):
            return raw
        if isinstance(raw, dict):
            return map_member7_response(raw)
        return StandardQAMatchResult(matched=False, reason="成员7返回类型无法识别")


def create_standard_qa_matcher(
    *,
    catalog: list[dict[str, Any]] | None = None,
    db_provider: Callable[[], Any] | None = None,
) -> StandardQAMatcher:
    """
    工厂：USE_MEMBER7_STANDARD_QA=1 且能导入 QAMatchingService 时走桥接，否则 Mock。
    """
    use_m7 = os.getenv("USE_MEMBER7_STANDARD_QA", "").strip() in {"1", "true", "TRUE", "yes"}
    if use_m7:
        try:
            from app.services.qa_matching_service import qa_matching_service  # type: ignore

            return Member7StandardQABridge(qa_matching_service, db_provider=db_provider)
        except Exception:
            pass
    return MockStandardQAMatcher(catalog=catalog)


class MockStandardQAMatcher:
    """测试替身：仅当问题精确命中预设库且一致性达标时视为可信。"""

    def __init__(self, catalog: list[dict[str, Any]] | None = None, threshold: float = 0.85):
        self.catalog = catalog or []
        self.threshold = threshold

    def match(
        self,
        question: str,
        keywords: list[str],
        entities: list[str],
        intent: str,
        access_context: dict[str, Any],
        knowledge_base_ids: list[str],
    ) -> StandardQAMatchResult:
        del intent
        q = question.strip()
        for item in self.catalog:
            if item.get("question") != q:
                continue
            kb_id = item.get("knowledge_base_id") or ""
            if knowledge_base_ids and kb_id not in knowledge_base_ids:
                return StandardQAMatchResult(
                    matched=False,
                    reason="知识库范围不一致",
                    status=item.get("status") or "",
                )
            entity_ok = 1.0
            item_entities = set(item.get("entities") or [])
            if entities and item_entities and not set(entities).issubset(item_entities | set(entities)):
                # 相似度高但实体不一致 -> 不可信
                if not item_entities.issuperset(set(entities)):
                    return StandardQAMatchResult(
                        matched=True,
                        qa_id=item.get("qa_id") or "",
                        answer=item.get("answer") or "",
                        semantic_score=0.9,
                        keyword_score=0.9,
                        entity_consistency=0.2,
                        scope_consistency=1.0,
                        final_score=0.4,
                        status=item.get("status") or "published",
                        reason="实体不一致，转入正式 RAG",
                        trusted=False,
                        source_document_ids=list(item.get("source_document_ids") or []),
                        knowledge_base_id=kb_id,
                    )
            scope_ok = 1.0
            deny = set(access_context.get("deny_document_ids") or [])
            src_docs = list(item.get("source_document_ids") or [])
            if any(d in deny for d in src_docs):
                scope_ok = 0.0
            final = min(0.95, 0.5 + 0.2 * entity_ok + 0.25 * scope_ok)
            trusted = (
                item.get("status") == "published"
                and final >= self.threshold
                and scope_ok >= 1.0
                and entity_ok >= 1.0
            )
            return StandardQAMatchResult(
                matched=True,
                qa_id=item.get("qa_id") or "",
                answer=item.get("answer") or "",
                variants=list(item.get("variants") or []),
                semantic_score=0.92,
                keyword_score=0.9,
                entity_consistency=entity_ok,
                scope_consistency=scope_ok,
                final_score=final,
                citations=list(item.get("citations") or []),
                status=item.get("status") or "",
                reason="可信命中" if trusted else "未达可信阈值",
                trusted=trusted,
                source_document_ids=src_docs,
                knowledge_base_id=kb_id,
            )
        return StandardQAMatchResult(matched=False, reason="未命中标准问答")
