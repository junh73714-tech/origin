"""
成员5：文档处理与向量索引模型补充迁移

新增表和字段:
1. document_process_logs -- 文档处理日志表
2. chunk_vectors -- pgvector 向量存储表
3. knowledge_bases、documents、document_versions、document_chunks、index_tasks 表新增字段

注意：knowledge_base_permissions 和 document_permissions 表由 005 统一创建
注意：qa_sources / question_variants 等标准问答表由 003 统一创建

Revision: 002
Depends: 001 (initial)
"""
from datetime import datetime

from alembic import op
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, ForeignKey, JSON,
)

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =====================================================================
    # 1. knowledge_bases 表新增字段
    # =====================================================================
    op.add_column("knowledge_bases", Column("status", String(50), nullable=False, server_default="active", comment="状态: active/disabled"))
    op.add_column("knowledge_bases", Column("business_domain", String(100), nullable=True, comment="业务领域"))
    op.add_column("knowledge_bases", Column("document_count", Integer, nullable=False, server_default="0", comment="文档数量"))
    op.add_column("knowledge_bases", Column("chunk_count", Integer, nullable=False, server_default="0", comment="Chunk数量"))
    op.create_index("ix_knowledge_bases_status", "knowledge_bases", ["tenant_id", "status"])

    # =====================================================================
    # 2. documents 表新增字段
    # =====================================================================
    op.add_column("documents", Column("original_filename", String(500), nullable=False, server_default="", comment="原始文件名"))
    op.add_column("documents", Column("mime_type", String(100), nullable=False, server_default="application/octet-stream", comment="MIME类型"))
    op.add_column("documents", Column("file_hash", String(64), nullable=False, server_default="", index=True, comment="文件SHA-256哈希"))
    op.add_column("documents", Column("page_count", Integer, nullable=True, comment="页数"))
    op.add_column("documents", Column("token_count", Integer, nullable=True, comment="Token数"))
    op.add_column("documents", Column("chunk_count", Integer, nullable=False, server_default="0", comment="Chunk数量"))
    op.add_column("documents", Column("processing_error", Text, nullable=True, comment="处理错误信息"))
    op.add_column("documents", Column("published_at", DateTime(timezone=True), nullable=True, comment="发布时间"))
    op.add_column("documents", Column("doc_metadata", JSON, nullable=True, comment="扩展元数据"))

    # =====================================================================
    # 3. document_versions 表新增字段
    # =====================================================================
    op.add_column("document_versions", Column("knowledge_base_id", String(64), nullable=False, server_default="", index=True, comment="所属知识库ID"))
    op.add_column("document_versions", Column("file_hash", String(64), nullable=False, server_default="", comment="文件SHA-256哈希"))
    op.add_column("document_versions", Column("previous_version", Integer, nullable=True, comment="上一版本号"))
    op.add_column("document_versions", Column("is_current_version", Boolean, nullable=False, server_default=op.f("false"), comment="是否为当前版本"))
    op.add_column("document_versions", Column("publish_status", String(50), nullable=False, server_default="draft", comment="版本发布状态"))
    op.add_column("document_versions", Column("effective_time", DateTime(timezone=True), nullable=True, comment="生效时间"))
    op.add_column("document_versions", Column("expiration_time", DateTime(timezone=True), nullable=True, comment="失效时间"))
    op.add_column("document_versions", Column("published_at", DateTime(timezone=True), nullable=True, comment="发布时间"))
    op.create_index("ix_document_versions_current", "document_versions", ["document_id", "is_current_version"])

    # =====================================================================
    # 4. document_chunks 表新增字段
    # =====================================================================
    op.add_column("document_chunks", Column("knowledge_base_id", String(64), nullable=False, server_default="", index=True, comment="知识库ID"))
    op.add_column("document_chunks", Column("document_version_id", String(64), nullable=False, server_default="", index=True, comment="文档版本ID"))
    op.add_column("document_chunks", Column("chunk_no", Integer, nullable=False, server_default="0", comment="切分序号"))
    op.add_column("document_chunks", Column("title_path", String(500), nullable=True, comment="标题路径"))
    op.add_column("document_chunks", Column("page_start", Integer, nullable=True, comment="起始页码"))
    op.add_column("document_chunks", Column("page_end", Integer, nullable=True, comment="结束页码"))
    op.add_column("document_chunks", Column("source_offset", Integer, nullable=False, server_default="0", comment="原文偏移位置"))
    op.add_column("document_chunks", Column("raw_text", Text, nullable=False, server_default="", comment="原始文本"))
    op.add_column("document_chunks", Column("clean_text", Text, nullable=False, server_default="", comment="清洗后文本"))
    op.add_column("document_chunks", Column("token_count", Integer, nullable=False, server_default="0", comment="Token计数"))
    op.add_column("document_chunks", Column("chunk_metadata", JSON, nullable=True, comment="元数据(JSON)"))
    op.add_column("document_chunks", Column("permission_metadata", JSON, nullable=True, comment="权限元数据"))
    op.add_column("document_chunks", Column("effective_time", DateTime(timezone=True), nullable=True, comment="生效时间"))
    op.add_column("document_chunks", Column("expiration_time", DateTime(timezone=True), nullable=True, comment="失效时间"))
    op.add_column("document_chunks", Column("status", String(50), nullable=False, server_default="active", comment="Chunk状态"))
    op.create_index("ix_document_chunks_version", "document_chunks", ["document_version_id", "chunk_no"])
    op.create_index("ix_document_chunks_status", "document_chunks", ["knowledge_base_id", "status"])

    # =====================================================================
    # 5. index_tasks 表新增字段
    # =====================================================================
    op.add_column("index_tasks", Column("document_version_id", String(64), nullable=False, server_default="", index=True, comment="文档版本ID"))
    op.add_column("index_tasks", Column("chunk_id", String(64), nullable=True, index=True, comment="Chunk ID"))
    op.add_column("index_tasks", Column("target", String(50), nullable=False, server_default="both", comment="索引目标: opensearch/pgvector/both"))
    op.add_column("index_tasks", Column("idempotent_key", String(128), nullable=False, server_default="", unique=True, comment="幂等键"))
    op.add_column("index_tasks", Column("retry_count", Integer, nullable=False, server_default="0", comment="重试次数"))
    op.add_column("index_tasks", Column("max_retries", Integer, nullable=False, server_default="3", comment="最大重试次数"))
    op.create_index("ix_index_tasks_version_target", "index_tasks", ["document_version_id", "target"])
    op.create_index("ix_index_tasks_idempotent", "index_tasks", ["idempotent_key"])

    # =====================================================================
    # 6. document_process_logs 表
    # =====================================================================
    op.create_table(
        "document_process_logs",
        Column("id", String(64), primary_key=True),
        Column("tenant_id", String(64), nullable=False, index=True),
        Column("document_id", String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        Column("document_version_id", String(64), nullable=True, index=True, comment="文档版本ID"),
        Column("stage", String(50), nullable=False, comment="处理阶段"),
        Column("status", String(50), nullable=False, default="pending", comment="状态"),
        Column("progress", Integer, nullable=False, default=0, comment="进度(0-100)"),
        Column("error_type", String(100), nullable=True, comment="错误类型"),
        Column("error_message", Text, nullable=True, comment="错误详情"),
        Column("error_stack", Text, nullable=True, comment="错误堆栈"),
        Column("started_at", DateTime(timezone=True), nullable=True, comment="开始时间"),
        Column("completed_at", DateTime(timezone=True), nullable=True, comment="完成时间"),
        Column("stage_metadata", JSON, nullable=True, comment="阶段元数据"),
        Column("created_at", DateTime(timezone=True), server_default=op.f("now()"), nullable=False),
        Column("updated_at", DateTime(timezone=True), server_default=op.f("now()"), nullable=False),
        Column("created_by", String(64), nullable=False),
        Column("updated_by", String(64), nullable=True),
    )
    op.create_index("ix_process_logs_doc_stage", "document_process_logs", ["document_id", "stage"])
    op.create_index("ix_process_logs_status", "document_process_logs", ["status"])

    # =====================================================================
    # 7. chunk_vectors 表 (pgvector)
    # =====================================================================
    # 注意: 需要先启用 pgvector 扩展 (CREATE EXTENSION IF NOT EXISTS vector)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunk_vectors",
        Column("id", String(64), primary_key=True),
        Column("tenant_id", String(64), nullable=False, index=True),
        Column("chunk_id", String(64), nullable=False, index=True),
        Column("document_id", String(64), nullable=False, index=True),
        Column("document_version_id", String(64), nullable=False, index=True),
        Column("knowledge_base_id", String(64), nullable=False, index=True),
        Column("embedding", String(20000), nullable=False, comment="向量数据(JSON数组格式)"),
        Column("model_version", String(16), nullable=False, comment="Embedding模型版本"),
        Column("dimension", Integer, nullable=False, comment="向量维度"),
        Column("permission_metadata", JSON, nullable=True, comment="权限元数据"),
        Column("created_at", DateTime(timezone=True), server_default=op.f("now()"), nullable=False),
    )
    # 使用 vector 类型的索引需要 pgvector 扩展
    # 实际生产环境建议使用: CREATE INDEX ON chunk_vectors USING ivfflat (embedding vector_cosine_ops)


def downgrade() -> None:
    # =====================================================================
    # 9. 删除 chunk_vectors 表
    # =====================================================================
    op.drop_table("chunk_vectors")

    # =====================================================================
    # 8. 删除 document_process_logs 表
    # =====================================================================
    op.drop_table("document_process_logs")

    # =====================================================================
    # 6. document_chunks 表删除新增字段
    # =====================================================================
    op.drop_index("ix_document_chunks_status", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version", table_name="document_chunks")
    op.drop_column("document_chunks", "status")
    op.drop_column("document_chunks", "expiration_time")
    op.drop_column("document_chunks", "effective_time")
    op.drop_column("document_chunks", "permission_metadata")
    op.drop_column("document_chunks", "chunk_metadata")
    op.drop_column("document_chunks", "token_count")
    op.drop_column("document_chunks", "clean_text")
    op.drop_column("document_chunks", "raw_text")
    op.drop_column("document_chunks", "source_offset")
    op.drop_column("document_chunks", "page_end")
    op.drop_column("document_chunks", "page_start")
    op.drop_column("document_chunks", "title_path")
    op.drop_column("document_chunks", "chunk_no")
    op.drop_column("document_chunks", "document_version_id")
    op.drop_column("document_chunks", "knowledge_base_id")

    # =====================================================================
    # 7. index_tasks 表删除新增字段
    # =====================================================================
    op.drop_index("ix_index_tasks_idempotent", table_name="index_tasks")
    op.drop_index("ix_index_tasks_version_target", table_name="index_tasks")
    op.drop_column("index_tasks", "max_retries")
    op.drop_column("index_tasks", "retry_count")
    op.drop_column("index_tasks", "idempotent_key")
    op.drop_column("index_tasks", "target")
    op.drop_column("index_tasks", "chunk_id")
    op.drop_column("index_tasks", "document_version_id")

    # =====================================================================
    # 5. document_versions 表删除新增字段
    # =====================================================================
    op.drop_index("ix_document_versions_current", table_name="document_versions")
    op.drop_column("document_versions", "published_at")
    op.drop_column("document_versions", "expiration_time")
    op.drop_column("document_versions", "effective_time")
    op.drop_column("document_versions", "publish_status")
    op.drop_column("document_versions", "is_current_version")
    op.drop_column("document_versions", "previous_version")
    op.drop_column("document_versions", "file_hash")
    op.drop_column("document_versions", "knowledge_base_id")

    # =====================================================================
    # 1. documents 表删除新增字段
    # =====================================================================
    op.drop_index("ix_documents_file_hash", table_name="documents")
    op.drop_index("ix_documents_kb_status", table_name="documents")
    op.drop_column("documents", "doc_metadata")
    op.drop_column("documents", "published_at")
    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "token_count")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "file_hash")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "original_filename")

    # =====================================================================
    # 2. knowledge_bases 表删除新增字段
    # =====================================================================
    op.drop_index("ix_knowledge_bases_status", table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "chunk_count")
    op.drop_column("knowledge_bases", "document_count")
    op.drop_column("knowledge_bases", "business_domain")
    op.drop_column("knowledge_bases", "status")
