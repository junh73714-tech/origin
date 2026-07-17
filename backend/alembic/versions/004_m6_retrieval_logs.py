"""成员6：Citation / QueryLog / RetrievalLog 表

Revision ID: 004
Revises: 003（成员4 identity/permission）
"""

from __future__ import annotations

import alembic.op as op
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "citations",
        Column("id", String(64), primary_key=True),
        Column("tenant_id", String(64), nullable=False, index=True),
        Column("citation_id", String(64), nullable=False, unique=True),
        Column("message_id", String(64), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        Column("query_id", String(64), nullable=True),
        Column("document_id", String(64), nullable=False),
        Column("document_version_id", String(64), nullable=False),
        Column("chunk_id", String(64), nullable=False),
        Column("document_name", String(255), nullable=False),
        Column("title_path", String(500)),
        Column("page_start", Integer),
        Column("page_end", Integer),
        Column("quote_text", Text),
        Column("source_status", String(50), nullable=False, server_default="published"),
        Column("is_current_version", Boolean, nullable=False, server_default="true"),
        Column("confidentiality_level", Integer, nullable=False, server_default="0"),
        Column("knowledge_base_id", String(64)),
        Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column("created_by", String(64), nullable=False),
        Column("updated_by", String(64)),
    )
    op.create_index("ix_citations_citation_id", "citations", ["citation_id"])
    op.create_index("ix_citations_doc_chunk", "citations", ["document_id", "chunk_id"])

    op.create_table(
        "query_logs",
        Column("id", String(64), primary_key=True),
        Column("tenant_id", String(64), nullable=False, index=True),
        Column("query_id", String(64), nullable=False, unique=True),
        Column("conversation_id", String(64)),
        Column("user_id", String(64), nullable=False),
        Column("original_query", Text, nullable=False),
        Column("rewritten_query", Text),
        Column("intent", String(100)),
        Column("answer_type", String(50)),
        Column("refusal_reason", String(255)),
        Column("scope_hash", String(64)),
        Column("trace_id", String(100)),
        Column("request_id", String(100)),
        Column("latency_ms", Integer),
        Column("cache_hit", Boolean, nullable=False, server_default="false"),
        Column("debug", JSONB),
        Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column("created_by", String(64), nullable=False),
        Column("updated_by", String(64)),
    )
    op.create_index("ix_query_logs_tenant_time", "query_logs", ["tenant_id", "created_at"])

    op.create_table(
        "retrieval_logs",
        Column("id", String(64), primary_key=True),
        Column("tenant_id", String(64), nullable=False, index=True),
        Column("query_id", String(64), nullable=False),
        Column("stage", String(50), nullable=False),
        Column("hit_count", Integer, nullable=False, server_default="0"),
        Column("latency_ms", Integer),
        Column("top_score", Float),
        Column("error", Text),
        Column("details", JSONB),
        Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column("created_by", String(64), nullable=False),
        Column("updated_by", String(64)),
    )
    op.create_index("ix_retrieval_logs_query_stage", "retrieval_logs", ["query_id", "stage"])


def downgrade() -> None:
    op.drop_index("ix_retrieval_logs_query_stage", table_name="retrieval_logs")
    op.drop_table("retrieval_logs")
    op.drop_index("ix_query_logs_tenant_time", table_name="query_logs")
    op.drop_table("query_logs")
    op.drop_index("ix_citations_doc_chunk", table_name="citations")
    op.drop_index("ix_citations_citation_id", table_name="citations")
    op.drop_table("citations")
