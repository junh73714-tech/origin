"""LangGraph 风格可序列化问答状态。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RAGState(BaseModel):
    """正式问答图状态。"""

    user_id: str = ""
    tenant_id: str = ""
    conversation_id: str | None = None
    original_query: str = ""
    rewritten_query: str = ""
    intent: str = ""
    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    access_context: dict[str, Any] = Field(default_factory=dict)
    standard_qa_result: dict[str, Any] | None = None
    keyword_results: list[dict[str, Any]] = Field(default_factory=list)
    vector_results: list[dict[str, Any]] = Field(default_factory=list)
    fused_results: list[dict[str, Any]] = Field(default_factory=list)
    reranked_results: list[dict[str, Any]] = Field(default_factory=list)
    selected_context: list[dict[str, Any]] = Field(default_factory=list)
    evidence_score: float = 0.0
    evidence_status: str = ""
    generated_answer: str = ""
    answer_type: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    refusal_reason: str | None = None
    confidence: float = 0.0
    trace_id: str = ""
    timings_ms: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    cancelled: bool = False
    debug: dict[str, Any] = Field(default_factory=dict)

    def freeze_access(self) -> dict[str, Any]:
        """返回当前权限快照副本。"""
        return dict(self.access_context)
