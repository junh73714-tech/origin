"""
文档相关 Schema
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BaseSchema


# ============ 知识库 Schema ============

class KnowledgeBaseCreate(BaseSchema):
    """创建知识库"""
    name: str = Field(..., min_length=1, max_length=255, description="名称")
    description: str | None = Field(default=None, description="描述")
    icon: str | None = Field(default=None, description="图标 URL")
    is_public: bool = Field(default=False, description="是否公开")
    settings: dict | None = Field(default=None, description="配置")


class KnowledgeBaseUpdate(BaseSchema):
    """更新知识库"""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = None
    is_public: bool | None = None
    settings: dict | None = None


class KnowledgeBaseResponse(BaseSchema):
    """知识库响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    icon: str | None = None
    is_public: bool
    settings: dict | None = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


# ============ 文档 Schema ============

class DocumentUploadResponse(BaseSchema):
    """文档上传响应"""
    document_id: str
    name: str
    file_type: str
    file_size: int
    status: str


class DocumentResponse(BaseSchema):
    """文档响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    name: str
    file_type: str
    file_size: int
    status: str
    char_count: int | None = None
    current_version: int
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应"""
    versions: list["DocumentVersionResponse"] = []
    chunk_count: int = 0


# ============ 文档版本 Schema ============

class DocumentVersionResponse(BaseSchema):
    """文档版本响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version: int
    file_size: int
    change_summary: str | None = None
    is_active: bool
    created_at: datetime


# ============ Chunk Schema ============

class ChunkResponse(BaseSchema):
    """Chunk 响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version: int
    content: str
    chunk_index: int
    char_start: int
    char_end: int
    metadata: dict | None = None
    index_status: str
    created_at: datetime


class ChunkPreviewResponse(BaseSchema):
    """Chunk 预览响应"""
    id: str
    content: str
    chunk_index: int
    document_name: str
    relevance_score: float | None = None


# ============ 索引任务 Schema ============

class IndexTaskResponse(BaseSchema):
    """索引任务响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    task_type: str
    status: str
    progress: int
    total_chunks: int
    indexed_chunks: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


# Forward reference
DocumentResponse.model_rebuild()
DocumentDetailResponse.model_rebuild()
