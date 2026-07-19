"""成员6拥有的 Citation / QueryLog / RetrievalLog 模型。"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Citation(BaseModel):
    """回答引用。"""

    __tablename__ = "citations"

    citation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    message_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True
    )
    query_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_status: Mapped[str] = mapped_column(String(50), nullable=False, default="published")
    is_current_version: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidentiality_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (Index("ix_citations_doc_chunk", "document_id", "chunk_id"),)


class QueryLog(BaseModel):
    """查询日志。"""

    __tablename__ = "query_logs"

    query_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_query: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    answer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    refusal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    debug: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("ix_query_logs_tenant_time", "tenant_id", "created_at"),)


class RetrievalLog(BaseModel):
    """检索阶段日志。"""

    __tablename__ = "retrieval_logs"

    query_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)  # keyword/vector/rrf/rerank
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("ix_retrieval_logs_query_stage", "query_id", "stage"),)
