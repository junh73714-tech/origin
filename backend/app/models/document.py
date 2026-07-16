"""
文档相关模型
包括知识库、文档、文档版本、Chunk等
"""
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class KnowledgeBase(BaseModel):
    """知识库模型"""

    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)  # 公开知识库

    # 配置
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 关系
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="knowledge_base")

    __table_args__ = (
        Index("ix_knowledge_bases_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase {self.name}>"


class Document(BaseModel):
    """文档模型"""

    __tablename__ = "documents"

    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # MinIO 路径
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    char_count: Mapped[int | None] = mapped_column(nullable=True)
    doc_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 当前版本
    current_version: Mapped[int] = mapped_column(default=1, nullable=False)

    # 关系
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document")
    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document")

    __table_args__ = (
        Index("ix_documents_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Document {self.name}>"


class DocumentVersion(BaseModel):
    """文档版本模型"""

    __tablename__ = "document_versions"

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # 关系
    document: Mapped["Document"] = relationship("Document", back_populates="versions")

    __table_args__ = (
        Index("ix_document_versions_doc_version", "document_id", "version", unique=True),
    )

    def __repr__(self) -> str:
        return f"<DocumentVersion {self.document_id} v{self.version}>"


class DocumentChunk(BaseModel):
    """文档 Chunk 模型"""

    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(nullable=False)  # 所属文档版本
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(nullable=False)  # 在文档中的顺序
    char_start: Mapped[int] = mapped_column(nullable=False)  # 在原文中的起始位置
    char_end: Mapped[int] = mapped_column(nullable=False)  # 在原文中的结束位置
    chunk_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    index_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # 关系
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_document_chunks_doc_index", "document_id", "chunk_index"),
        Index("ix_document_chunks_hash", "content_hash"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.document_id} [{self.char_start}:{self.char_end}]>"


class IndexTask(BaseModel):
    """索引任务模型"""

    __tablename__ = "index_tasks"

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # keyword, vector, both
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(default=0, nullable=False)  # 0-100
    total_chunks: Mapped[int] = mapped_column(default=0, nullable=False)
    indexed_chunks: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_index_tasks_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<IndexTask {self.document_id} {self.task_type} {self.status}>"
