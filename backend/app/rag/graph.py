"""
正式问答图（LangGraph 风格节点流水线）。

各节点独立可测试：明确输入/输出、超时边界、异常转换、结构化日志与耗时。
未引入重型 langgraph 依赖，节点签名保持可替换为真实 LangGraph。
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from app.core.logging import get_logger
from app.core.security import AccessContext
from app.prompts.qa_system import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from app.providers.llm.provider import LLMProvider, get_llm_provider
from app.providers.reranker.provider import RerankerProvider, get_reranker_provider
from app.rag.context_builder import assemble_context
from app.rag.evidence import assess_evidence
from app.rag.metrics import observe_stage
from app.rag.preprocess import preprocess
from app.rag.safety import check_input_safety, check_output_safety
from app.rag.standard_qa_adapter import MockStandardQAMatcher, StandardQAMatcher
from app.rag.state import RAGState
from app.retrieval.permission_adapter import (
    DefaultPermissionAdapter,
    compute_scope_hash,
    ensure_access_snapshot,
)
from app.retrieval.service import HybridRetrievalService
from app.retrieval.types import RetrievalHit

logger = get_logger(__name__)

NodeFn = Callable[[RAGState], RAGState]


def _timed(state: RAGState, name: str, fn: Callable[[], None]) -> None:
    started = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - started
    state.timings_ms[name] = int(elapsed * 1000)
    observe_stage(name, elapsed)


class QAGraph:
    """正式问答图执行器。"""

    def __init__(
        self,
        retrieval: HybridRetrievalService,
        llm: LLMProvider | None = None,
        reranker: RerankerProvider | None = None,
        standard_qa: StandardQAMatcher | None = None,
        permission: DefaultPermissionAdapter | None = None,
        token_budget: int = 3000,
    ):
        self.retrieval = retrieval
        self.llm = llm or get_llm_provider()
        self.reranker = reranker or get_reranker_provider()
        self.standard_qa = standard_qa or MockStandardQAMatcher()
        self.permission = permission or DefaultPermissionAdapter()
        self.token_budget = token_budget

    def run(
        self,
        query: str,
        access: AccessContext,
        conversation_id: str | None = None,
        trace_id: str | None = None,
        history: list[str] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> RAGState:
        access = ensure_access_snapshot(access)
        if not getattr(access, "scope_hash", None):
            access.scope_hash = compute_scope_hash(access)

        state = RAGState(
            user_id=access.user_id,
            tenant_id=access.tenant_id,
            conversation_id=conversation_id,
            original_query=query,
            access_context=access.to_dict()
            | {
                "scope_hash": getattr(access, "scope_hash", ""),
                "deny_document_ids": list(getattr(access, "deny_document_ids", []) or []),
                "knowledge_base_ids": list(
                    getattr(access, "knowledge_base_ids", None)
                    or (access.data_scopes or {}).get("knowledge_base", [])
                    or []
                ),
                "max_confidentiality_level": getattr(
                    access, "max_confidentiality_level", 0
                ),
                "temporary_grants": list(getattr(access, "temporary_grants", []) or []),
            },
            trace_id=trace_id or f"tr_{uuid.uuid4().hex[:16]}",
        )

        def cancelled() -> bool:
            return bool(cancel_check and cancel_check())

        # 0) 输入安全检查
        input_safe = check_input_safety(query)
        state.debug["input_safety"] = {"ok": input_safe.ok, "reasons": input_safe.reasons}
        query_for_graph = input_safe.sanitized_text or query

        # 1) 预处理
        def do_preprocess() -> None:
            pre = preprocess(query_for_graph, history=history)
            state.original_query = pre.original_query
            state.rewritten_query = pre.rewritten_query
            state.intent = pre.intent
            state.keywords = pre.keywords
            state.entities = pre.entities
            state.timings_ms.update({f"pre_{k}": v for k, v in pre.timings_ms.items()})

        _timed(state, "preprocess", do_preprocess)
        if cancelled():
            state.cancelled = True
            state.refusal_reason = "用户取消"
            return state

        if state.intent == "refuse_or_guide":
            state.answer_type = "refusal"
            state.generated_answer = "该问题超出企业知识范围，请改问与制度、流程或产品相关的问题。"
            state.refusal_reason = "非企业知识"
            state.evidence_status = "out_of_scope"
            return state

        # 2) 标准问答匹配
        def do_std() -> None:
            kb_ids = list(state.access_context.get("knowledge_base_ids") or [])
            result = self.standard_qa.match(
                question=state.rewritten_query,
                keywords=state.keywords,
                entities=state.entities,
                intent=state.intent,
                access_context=state.access_context,
                knowledge_base_ids=kb_ids,
            )
            state.standard_qa_result = result.model_dump()
            if result.trusted and self.permission.can_access_standard_qa(
                access, result.model_dump()
            ):
                state.generated_answer = result.answer
                state.answer_type = "standard_qa"
                state.citations = result.citations
                state.confidence = result.final_score
                state.evidence_status = "trusted_standard_qa"

        _timed(state, "standard_qa", do_std)
        if state.answer_type == "standard_qa":
            # 标准问答路径也做输出安全与引用二次校验
            out = check_output_safety(state.generated_answer)
            state.generated_answer = out.sanitized_text
            state.debug["output_safety"] = {"ok": out.ok, "reasons": out.reasons}
            validated: list[dict[str, Any]] = []
            for cit in state.citations:
                if self.permission.can_open_citation(
                    access, cit | {"tenant_id": access.tenant_id}
                ):
                    validated.append(cit)
            state.citations = validated
            return state

        # 3) 混合检索
        mode = {
            "keyword_prefer": "keyword",
            "vector_prefer": "vector",
            "hybrid": "hybrid",
            "standard_qa_prefer": "hybrid",
        }.get(state.intent, "hybrid")

        def do_retrieve() -> None:
            try:
                hybrid = self.retrieval.retrieve(
                    state.rewritten_query, access, top_k=20, mode=mode
                )
            except Exception as exc:  # noqa: BLE001
                state.errors["retrieval"] = str(exc)
                return
            state.keyword_results = [h.model_dump() for h in hybrid.keyword_hits]
            state.vector_results = [h.model_dump() for h in hybrid.vector_hits]
            state.fused_results = [h.model_dump() for h in hybrid.fused_hits]
            state.errors.update(hybrid.errors)

        _timed(state, "retrieval", do_retrieve)
        if cancelled():
            state.cancelled = True
            state.refusal_reason = "用户取消"
            return state

        fused_hits = [RetrievalHit.model_validate(x) for x in state.fused_results]

        # 4) Rerank
        def do_rerank() -> None:
            if not fused_hits:
                return
            try:
                ranked = self.reranker.rerank(state.rewritten_query, fused_hits)
            except Exception as exc:  # noqa: BLE001
                state.errors["reranker"] = str(exc)
                # 降级：使用 fused 顺序，不绕过权限
                state.reranked_results = [h.model_dump() for h in fused_hits]
                return
            id_to_hit = {h.chunk_id: h for h in fused_hits}
            ordered: list[RetrievalHit] = []
            for item in ranked:
                hit = id_to_hit.get(item.chunk_id)
                if hit:
                    cloned = hit.model_copy(deep=True)
                    cloned.score = item.score
                    cloned.rank = item.rank
                    cloned.source = "reranked"
                    ordered.append(cloned)
            state.reranked_results = [h.model_dump() for h in ordered]
            state.debug["reranker_mock"] = getattr(self.reranker, "is_bound", False) is False

        _timed(state, "rerank", do_rerank)
        if cancelled():
            state.cancelled = True
            state.refusal_reason = "用户取消"
            return state

        candidates = [
            RetrievalHit.model_validate(x)
            for x in (state.reranked_results or state.fused_results)
        ]

        # 5) 证据覆盖
        assessment = assess_evidence(state.rewritten_query, candidates)
        state.evidence_score = assessment.coverage_score
        state.evidence_status = assessment.decision
        state.debug["evidence"] = {
            "covered": assessment.covered,
            "missing": assessment.missing,
            "conflicts": assessment.conflicts,
            "rule_version": assessment.rule_version,
        }

        if assessment.decision in {"refuse"}:
            state.answer_type = "refusal"
            state.generated_answer = "未找到足够有效证据，无法回答该问题。"
            state.refusal_reason = "证据不足"
            return state
        if assessment.decision == "conflict":
            state.answer_type = "reference"
            state.refusal_reason = "证据冲突"
        if assessment.decision == "ask_user":
            state.answer_type = "reference"
            state.generated_answer = (
                "现有证据仅部分覆盖问题条件，缺少："
                + "、".join(assessment.missing)
                + "。请补充后重试。"
            )
            state.refusal_reason = "需要用户补充"
        if assessment.decision == "supplement" and candidates:
            state.debug["supplement_needed"] = assessment.missing

        # 6) 上下文组装
        ctx = assemble_context(
            candidates, tenant_id=access.tenant_id, token_budget=self.token_budget
        )
        state.selected_context = [
            {
                "citation_id": s.citation_id,
                "document_id": s.document_id,
                "document_version_id": s.document_version_id,
                "chunk_id": s.chunk_id,
                "document_name": s.document_name,
                "title_path": s.title_path,
                "page_start": s.page_start,
                "page_end": s.page_end,
                "status": s.status,
                "permission_summary": s.permission_summary,
                "quote": s.text,
                "is_current_version": True,
            }
            for s in ctx.snippets
        ]

        # 7) 生成或拒答
        if not ctx.snippets and state.answer_type != "reference":
            state.answer_type = "refusal"
            state.generated_answer = "无有效证据，拒绝回答。"
            state.refusal_reason = "无有效证据"
            return state

        # ask_user 已给出引导文案，不再调用 LLM
        skip_llm = assessment.decision == "ask_user" and bool(state.generated_answer)

        if not skip_llm:
            evidence_status = "ok"
            if assessment.decision == "conflict":
                evidence_status = "conflict"
            elif assessment.decision in {"ask_user", "supplement"}:
                evidence_status = "partial"
            if state.errors.get("retrieval") and not candidates:
                evidence_status = "insufficient"

            user_prompt = build_user_prompt(
                state.rewritten_query, ctx.prompt_block, evidence_status
            )
            if "忽略以上指令" in user_prompt or "ignore previous" in user_prompt.lower():
                state.debug["prompt_injection_detected"] = True
                user_prompt = user_prompt.replace("忽略以上指令", "[已屏蔽]")

            def do_llm() -> None:
                if cancelled():
                    state.cancelled = True
                    state.refusal_reason = "用户取消"
                    return
                try:
                    result = self.llm.generate(SYSTEM_PROMPT, user_prompt)
                except Exception as exc:  # noqa: BLE001
                    state.errors["llm"] = str(exc)
                    state.answer_type = "refusal"
                    state.generated_answer = "模型服务暂时不可用，请稍后重试。"
                    state.refusal_reason = "LLM 失败"
                    return
                if state.answer_type != "reference":
                    state.generated_answer = result.answer
                    state.answer_type = result.answer_type
                elif not state.generated_answer:
                    state.generated_answer = result.answer
                state.confidence = result.confidence
                if result.refusal_reason:
                    state.refusal_reason = result.refusal_reason
                state.debug["llm"] = {
                    "model": result.model_name,
                    "version": result.model_version,
                    "prompt_version": result.prompt_version or PROMPT_VERSION,
                    "is_mock": result.is_mock,
                    "token_usage": result.token_usage,
                }

            _timed(state, "llm", do_llm)
            if state.cancelled:
                return state

        # 8) 输出安全检查
        out = check_output_safety(state.generated_answer or "")
        state.generated_answer = out.sanitized_text
        state.debug["output_safety"] = {"ok": out.ok, "reasons": out.reasons}

        # 9) 引用权限二次校验（存在性/状态/权限）
        citations: list[dict[str, Any]] = []
        for snip in state.selected_context:
            if snip.get("status") in {"paused", "offlined", "expired"}:
                continue
            if snip.get("is_current_version") is False:
                continue
            ok = self.permission.can_open_citation(access, snip | {"tenant_id": access.tenant_id})
            if not ok:
                logger.warning(
                    "citation_denied",
                    citation_id=snip.get("citation_id"),
                    user_id=access.user_id,
                )
                continue
            quote = snip.get("quote") or ""
            # 引用片段与答案弱一致性：拒答可不要求匹配
            if state.answer_type not in {"refusal", "reference"} and quote:
                overlap = any(
                    tok and tok in (state.generated_answer or "")
                    for tok in quote[:40].split()
                ) or quote[:12] in (state.generated_answer or "")
                if not overlap and len(quote) > 20:
                    state.debug.setdefault("citation_mismatch", []).append(
                        snip.get("citation_id")
                    )
            citations.append(
                {
                    "citation_id": snip["citation_id"],
                    "document_name": snip.get("document_name"),
                    "document_version": snip.get("document_version_id"),
                    "document_version_id": snip.get("document_version_id"),
                    "title_path": snip.get("title_path"),
                    "page_start": snip.get("page_start"),
                    "page_end": snip.get("page_end"),
                    "quote": quote,
                    "source_status": snip.get("status"),
                    "document_id": snip.get("document_id"),
                    "chunk_id": snip.get("chunk_id"),
                    "knowledge_base_id": snip.get("knowledge_base_id"),
                    "is_current_version": snip.get("is_current_version", True),
                }
            )
        state.citations = citations
        logger.info(
            "qa_graph_done",
            trace_id=state.trace_id,
            answer_type=state.answer_type,
            timings=state.timings_ms,
        )
        return state
