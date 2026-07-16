"""
文档相关 Schema
包含知识库、文档、版本、Chunk、索引任务的请求和响应模型

成员5主责：所有文档生命周期相关的 Schema 定义
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BaseSchema, PaginationParams


# =============================================================================
# 知识库 Schema
# =============================================================================

class KnowledgeBaseCreate(BaseSchema):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=255, description="知识库名称")
    description: str | None = Field(default=None, description="描述")
    icon: str | None = Field(default=None, description="图标URL")
    is_public: bool = Field(default=False, description="是否公开")
    business_domain: str | None = Field(default=None, max_length=100, description="业务领域")
    settings: dict | None = Field(default=None, description="知识库配置")


class KnowledgeBaseUpdate(BaseSchema):
    """更新知识库请求"""
    name: str | None = Field(default=None, min_length=1, max_length=255, description="名称")
    description: str | None = Field(default=None, description="描述")
    icon: str | None = Field(default=None, description="图标URL")
    is_public: bool | None = Field(default=None, description="是否公开")
    business_domain: str | None = Field(default=None, max_length=100, description="业务领域")
    settings: dict | None = Field(default=None, description="知识库配置")


class KnowledgeBaseResponse(BaseSchema):
    """知识库响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="知识库ID")
    name: str = Field(..., description="名称")
    description: str | None = Field(default=None, description="描述")
    icon: str | None = Field(default=None, description="图标URL")
    is_public: bool = Field(default=False, description="是否公开")
    status: str = Field(default="active", description="状态: active/disabled")
    business_domain: str | None = Field(default=None, description="业务领域")
    settings: dict | None = Field(default=None, description="配置")
    document_count: int = Field(default=0, description="文档数量")
    chunk_count: int = Field(default=0, description="Chunk数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class KnowledgeBaseDetailResponse(KnowledgeBaseResponse):
    """知识库详情响应"""
    created_by: str = Field(..., description="创建人")
    updated_by: str | None = Field(default=None, description="更新人")


class KnowledgeBaseStatsResponse(BaseSchema):
    """知识库统计响应"""
    knowledge_base_id: str = Field(..., description="知识库ID")
    document_count: int = Field(default=0, description="文档总数")
    published_count: int = Field(default=0, description="已发布文档数")
    processing_count: int = Field(default=0, description="处理中文档数")
    failed_count: int = Field(default=0, description="处理失败文档数")
    chunk_count: int = Field(default=0, description="Chunk总数")
    indexed_chunk_count: int = Field(default=0, description="已索引Chunk数")
    total_tokens: int = Field(default=0, description="总Token数")
    index_task_pending: int = Field(default=0, description="待处理索引任务数")
    index_task_failed: int = Field(default=0, description="失败索引任务数")


class KnowledgeBaseListParams(PaginationParams):
    """知识库列表查询参数"""
    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="状态筛选: active/disabled")


# =============================================================================
# 知识库权限 Schema
# =============================================================================

class KnowledgeBasePermissionCreate(BaseSchema):
    """创建知识库权限请求"""
    principal_type: str = Field(..., description="主体类型: user/role/department/user_group")
    principal_id: str = Field(..., description="主体ID")
    permission_type: str = Field(..., description="权限类型: read/write/admin")
    is_deny: bool = Field(default=False, description="是否为显式拒绝")
    effective_time: datetime | None = Field(default=None, description="生效时间")
    expiration_time: datetime | None = Field(default=None, description="失效时间")


class KnowledgeBasePermissionResponse(BaseSchema):
    """知识库权限响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="权限ID")
    knowledge_base_id: str = Field(..., description="知识库ID")
    principal_type: str = Field(..., description="主体类型")
    principal_id: str = Field(..., description="主体ID")
    permission_type: str = Field(..., description="权限类型")
    is_deny: bool = Field(default=False, description="是否为显式拒绝")
    effective_time: datetime | None = Field(default=None, description="生效时间")
    expiration_time: datetime | None = Field(default=None, description="失效时间")
    created_at: datetime = Field(..., description="创建时间")


# =============================================================================
# 文档 Schema
# =============================================================================

class DocumentUploadResponse(BaseSchema):
    """文档上传响应"""
    document_id: str = Field(..., description="文档ID")
    name: str = Field(..., description="文档名称")
    file_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小(字节)")
    file_hash: str = Field(..., description="文件SHA-256哈希")
    status: str = Field(..., description="文档状态")


class DocumentResponse(BaseSchema):
    """文档响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="文档ID")
    knowledge_base_id: str = Field(..., description="所属知识库ID")
    name: str = Field(..., description="文档名称")
    original_filename: str = Field(..., description="原始文件名")
    file_type: str = Field(..., description="文件类型")
    mime_type: str = Field(..., description="MIME类型")
    file_size: int = Field(..., description="文件大小(字节)")
    file_hash: str = Field(..., description="文件SHA-256哈希")
    status: str = Field(..., description="文档状态")
    page_count: int | None = Field(default=None, description="页数")
    char_count: int | None = Field(default=None, description="字符数")
    token_count: int | None = Field(default=None, description="Token数")
    current_version: int = Field(..., description="当前版本号")
    processing_error: str | None = Field(default=None, description="处理错误信息")
    published_at: datetime | None = Field(default=None, description="发布时间")
    doc_metadata: dict | None = Field(default=None, description="扩展元数据")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应"""
    created_by: str = Field(..., description="创建人")
    updated_by: str | None = Field(default=None, description="更新人")
    versions: list["DocumentVersionResponse"] = Field(default_factory=list, description="版本列表")
    chunk_count: int = Field(default=0, description="Chunk数量")


class DocumentListParams(PaginationParams):
    """文档列表查询参数"""
    knowledge_base_id: str | None = Field(default=None, description="知识库ID筛选")
    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="状态筛选")
    file_type: str | None = Field(default=None, description="文件类型筛选")


# =============================================================================
# 文档版本 Schema
# =============================================================================

class DocumentVersionResponse(BaseSchema):
    """文档版本响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="版本ID")
    document_id: str = Field(..., description="文档ID")
    knowledge_base_id: str = Field(..., description="知识库ID")
    version: int = Field(..., description="版本号")
    file_size: int = Field(..., description="文件大小(字节)")
    file_hash: str = Field(..., description="文件SHA-256哈希")
    previous_version: int | None = Field(default=None, description="上一版本号")
    is_current_version: bool = Field(default=False, description="是否为当前版本")
    change_summary: str | None = Field(default=None, description="变更说明")
    publish_status: str = Field(..., description="版本发布状态")
    effective_time: datetime | None = Field(default=None, description="生效时间")
    expiration_time: datetime | None = Field(default=None, description="失效时间")
    published_at: datetime | None = Field(default=None, description="发布时间")
    created_at: datetime = Field(..., description="创建时间")


# =============================================================================
# Chunk Schema
# =============================================================================

class ChunkResponse(BaseSchema):
    """Chunk响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="文档ID")
    document_version_id: str = Field(..., description="文档版本ID")
    knowledge_base_id: str = Field(..., description="知识库ID")
    chunk_no: int = Field(..., description="切分序号")
    title_path: str | None = Field(default=None, description="标题路径")
    page_start: int | None = Field(default=None, description="起始页码")
    page_end: int | None = Field(default=None, description="结束页码")
    clean_text: str = Field(..., description="清洗后文本")
    token_count: int = Field(default=0, description="Token计数")
    status: str = Field(..., description="Chunk状态")
    index_status: str = Field(..., description="索引状态")
    created_at: datetime = Field(..., description="创建时间")


class ChunkDetailResponse(ChunkResponse):
    """Chunk详情响应"""
    raw_text: str = Field(..., description="原始文本")
    source_offset: int = Field(default=0, description="原文偏移位置")
    content_hash: str = Field(..., description="内容哈希")
    chunk_metadata: dict | None = Field(default=None, description="元数据")
    effective_time: datetime | None = Field(default=None, description="生效时间")
    expiration_time: datetime | None = Field(default=None, description="失效时间")


class ChunkListParams(PaginationParams):
    """Chunk列表查询参数"""
    document_id: str | None = Field(default=None, description="文档ID筛选")
    document_version_id: str | None = Field(default=None, description="版本ID筛选")
    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="Chunk状态筛选")


# =============================================================================
# 索引任务 Schema
# =============================================================================

class IndexTaskResponse(BaseSchema):
    """索引任务响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="任务ID")
    document_id: str = Field(..., description="文档ID")
    document_version_id: str = Field(..., description="文档版本ID")
    chunk_id: str | None = Field(default=None, description="Chunk ID")
    task_type: str = Field(..., description="任务类型: create/update/delete/rebuild/consistency_check")
    target: str = Field(..., description="索引目标: opensearch/pgvector/both")
    idempotent_key: str = Field(..., description="幂等键")
    status: str = Field(..., description="状态: pending/processing/completed/failed")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    progress: int = Field(default=0, description="进度(0-100)")
    total_chunks: int = Field(default=0, description="总Chunk数")
    indexed_chunks: int = Field(default=0, description="已索引Chunk数")
    error_message: str | None = Field(default=None, description="错误信息")
    started_at: datetime | None = Field(default=None, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    created_at: datetime = Field(..., description="创建时间")


class IndexTaskListParams(PaginationParams):
    """索引任务列表查询参数"""
    document_id: str | None = Field(default=None, description="文档ID筛选")
    status: str | None = Field(default=None, description="状态筛选")
    task_type: str | None = Field(default=None, description="任务类型筛选")


class IndexRebuildRequest(BaseSchema):
    """重建索引请求"""
    document_id: str | None = Field(default=None, description="指定文档ID(为空则全量重建)")
    knowledge_base_id: str | None = Field(default=None, description="指定知识库ID(为空则全量重建)")


class ConsistencyCheckRequest(BaseSchema):
    """一致性检查请求"""
    knowledge_base_id: str | None = Field(default=None, description="指定知识库ID")
    auto_fix: bool = Field(default=False, description="是否自动修复不一致")


# Forward references
DocumentDetailResponse.model_rebuild()
