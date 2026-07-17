"""
文档相关模型
包括知识库、文档、文档版本、Chunk、索引任务、处理日志等

成员5主责：所有文档生命周期相关数据模型
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


# =============================================================================
# 知识库模型
# =============================================================================

class KnowledgeBase(BaseModel):
    """知识库模型

    管理知识库的基本信息和生命周期状态。
    知识库停用后不允许新检索，但不删除历史数据。
    """

    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="知识库名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="图标URL")
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否公开知识库")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", comment="状态: active(启用)/disabled(停用)"
    )
    business_domain: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="业务领域"
    )
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="知识库配置")
    # 统计字段（由异步任务定期更新或实时计算）
    document_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="文档数量")
    chunk_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="Chunk数量")

    # 关系
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="knowledge_base", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_knowledge_bases_tenant_name", "tenant_id", "name"),
        Index("ix_knowledge_bases_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase {self.name} [{self.status}]>"


# =============================================================================
# 文档模型
# =============================================================================

class Document(BaseModel):
    """文档模型

    管理文档元信息、状态流转和处理进度。
    文档状态机: draft -> processing -> pending_review -> pending_publish -> published
    published -> paused/expired/offline
    """

    __tablename__ = "documents"

    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库ID",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="文档名称")
    original_filename: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="原始文件名"
    )
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="文件类型: pdf/docx/txt/md/html"
    )
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="MIME类型"
    )
    file_size: Mapped[int] = mapped_column(nullable=False, comment="文件大小(字节)")
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="文件SHA-256哈希"
    )
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="MinIO存储路径"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft",
        comment="文档状态: draft/processing/failed/pending_review/pending_publish/published/paused/expired/offline/archived"
    )
    page_count: Mapped[int | None] = mapped_column(nullable=True, comment="页数")
    char_count: Mapped[int | None] = mapped_column(nullable=True, comment="字符数")
    token_count: Mapped[int | None] = mapped_column(nullable=True, comment="Token数")
    processing_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="处理错误信息"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布时间"
    )
    chunk_count: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="Chunk数量"
    )
    doc_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, comment="扩展元数据"
    )
    # 当前版本号
    current_version: Mapped[int] = mapped_column(default=1, nullable=False, comment="当前版本号")

    # 关系
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase", back_populates="documents"
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", lazy="selectin"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", lazy="selectin"
    )
    process_logs: Mapped[list["DocumentProcessLog"]] = relationship(
        "DocumentProcessLog", back_populates="document", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_documents_tenant_status", "tenant_id", "status"),
        Index("ix_documents_kb_status", "knowledge_base_id", "status"),
        Index("ix_documents_file_hash", "tenant_id", "file_hash"),
    )

    def __repr__(self) -> str:
        return f"<Document {self.name} [{self.status}] v{self.current_version}>"


# =============================================================================
# 文档版本模型
# =============================================================================

class DocumentVersion(BaseModel):
    """文档版本模型

    记录文档每个版本的文件信息、变更说明和发布状态。
    版本更新流程: 上传新版本 -> 解析切分 -> 比较差异 -> 增量索引 -> 验证 -> 发布
    """

    __tablename__ = "document_versions"

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属文档ID",
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="所属知识库ID(冗余，加速查询)"
    )
    version: Mapped[int] = mapped_column(nullable=False, comment="版本号(递增)")
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="MinIO存储路径"
    )
    file_size: Mapped[int] = mapped_column(nullable=False, comment="文件大小(字节)")
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="文件SHA-256哈希"
    )
    previous_version: Mapped[int | None] = mapped_column(
        nullable=True, comment="上一版本号"
    )
    is_current_version: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="是否为当前版本"
    )
    change_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="变更说明"
    )
    publish_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft",
        comment="版本发布状态: draft/processing/failed/pending_review/pending_publish/published/offline/archived"
    )
    effective_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="生效时间"
    )
    expiration_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="失效时间"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布时间"
    )

    # 关系
    document: Mapped["Document"] = relationship(
        "Document", back_populates="versions"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document_version", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_document_versions_doc_version", "document_id", "version", unique=True),
        Index("ix_document_versions_current", "document_id", "is_current_version"),
    )

    def __repr__(self) -> str:
        return f"<DocumentVersion {self.document_id} v{self.version} [{self.publish_status}]>"


# =============================================================================
# 文档Chunk模型
# =============================================================================

class DocumentChunk(BaseModel):
    """文档Chunk模型

    文档切分后的最小检索单元。
    每个Chunk必须可追溯到原文、页码、标题和文档版本。
    Chunk权限继承文档权限，permission_metadata存储权限快照。
    """

    __tablename__ = "document_chunks"

    # 层级归属
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="知识库ID(冗余，加速检索过滤)"
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文档ID",
    )
    document_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文档版本ID",
    )

    # 切分信息
    chunk_no: Mapped[int] = mapped_column(nullable=False, comment="切分序号(从1开始)")
    title_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="标题路径(层级标题链，用 > 分隔)"
    )
    page_start: Mapped[int | None] = mapped_column(nullable=True, comment="起始页码")
    page_end: Mapped[int | None] = mapped_column(nullable=True, comment="结束页码")
    source_offset: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="原文偏移位置(字符位置)"
    )

    # 文本内容
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, comment="原始文本")
    clean_text: Mapped[str] = mapped_column(Text, nullable=False, comment="清洗后文本")
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="内容哈希(用于差异对比)"
    )
    token_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="Token计数")

    # 元数据
    chunk_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, comment="元数据(JSON)"
    )
    permission_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="权限元数据(继承自文档，存储AccessContext快照)"
    )

    # 时间控制
    effective_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="生效时间"
    )
    expiration_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="失效时间"
    )

    # 状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active",
        comment="Chunk状态: active/outdated/deleted"
    )
    index_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending",
        comment="索引状态: pending/indexing/indexed/failed"
    )

    # 关系
    document: Mapped["Document"] = relationship(
        "Document", back_populates="chunks"
    )
    document_version: Mapped["DocumentVersion"] = relationship(
        "DocumentVersion", back_populates="chunks"
    )

    __table_args__ = (
        Index("ix_document_chunks_doc_index", "document_id", "chunk_no"),
        Index("ix_document_chunks_version", "document_version_id", "chunk_no"),
        Index("ix_document_chunks_hash", "content_hash"),
        Index("ix_document_chunks_status", "knowledge_base_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id} v={self.document_version_id} no={self.chunk_no}>"


# =============================================================================
# 索引任务模型
# =============================================================================

class IndexTask(BaseModel):
    """索引任务模型

    管理文档索引写入任务，支持幂等写入和可重试机制。
    索引目标: OpenSearch(BM25关键词索引) + pgvector(向量索引)
    只有两种索引都达到可用状态，文档才具备发布条件。
    """

    __tablename__ = "index_tasks"

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文档ID",
    )
    document_version_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="文档版本ID"
    )
    chunk_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="Chunk ID(批量任务为空)"
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="任务类型: create/update/delete/rebuild/consistency_check"
    )
    target: Mapped[str] = mapped_column(
        String(50), nullable=False, default="both",
        comment="索引目标: opensearch/pgvector/both"
    )
    idempotent_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, comment="幂等键"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending",
        comment="状态: pending/processing/completed/failed"
    )
    retry_count: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="重试次数"
    )
    max_retries: Mapped[int] = mapped_column(
        default=3, nullable=False, comment="最大重试次数"
    )
    progress: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="进度(0-100)"
    )
    total_chunks: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="总Chunk数"
    )
    indexed_chunks: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="已索引Chunk数"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    __table_args__ = (
        Index("ix_index_tasks_status", "status"),
        Index("ix_index_tasks_version_target", "document_version_id", "target"),
        Index("ix_index_tasks_idempotent", "idempotent_key"),
    )

    def __repr__(self) -> str:
        return f"<IndexTask {self.task_type}->{self.target} [{self.status}]>"


# =============================================================================
# 文档处理日志模型
# =============================================================================

class DocumentProcessLog(BaseModel):
    """文档处理日志模型

    记录文档处理的每个阶段和结果。
    用于问题排查、重试决策和后台状态展示。
    """

    __tablename__ = "document_process_logs"

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文档ID",
    )
    document_version_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="文档版本ID"
    )
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="处理阶段: upload/parse/clean/split/embed/index_opensearch/index_pgvector/publish"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending",
        comment="状态: pending/processing/completed/failed"
    )
    progress: Mapped[int] = mapped_column(
        default=0, nullable=False, comment="当前阶段进度(0-100)"
    )
    error_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="错误类型"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误详情"
    )
    error_stack: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误堆栈(仅开发环境)"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )
    stage_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, comment="阶段元数据(解析结果统计等)"
    )

    # 关系
    document: Mapped["Document"] = relationship(
        "Document", back_populates="process_logs"
    )

    __table_args__ = (
        Index("ix_process_logs_doc_stage", "document_id", "stage"),
        Index("ix_process_logs_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<DocumentProcessLog doc={self.document_id} stage={self.stage} [{self.status}]>"
