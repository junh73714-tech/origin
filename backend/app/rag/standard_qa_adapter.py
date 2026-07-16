"""
成员7标准问答匹配适配器。

只通过服务接口调用，不直接查询底层表/索引。
成员7未就绪时使用契约一致的测试替身。
"""
from __future__ import annotations

from typing import Any, Protocol

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
