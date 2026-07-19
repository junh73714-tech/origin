"""
Schema 导出
"""
from app.schemas.common import (
    BaseSchema,
    PaginationParams,
    SortParams,
    FilterParams,
    ListResponse,
    BulkOperationResult,
    HealthCheckResponse,
)
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    UserDetailResponse,
    RoleResponse,
    PermissionResponse,
    AccessTokenPayload,
)
from app.schemas.document import (
    # 知识库
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseDetailResponse,
    KnowledgeBaseStatsResponse,
    KnowledgeBasePermissionCreate,
    KnowledgeBasePermissionResponse,
    # 文档
    DocumentUploadResponse,
    DocumentResponse,
    DocumentDetailResponse,
    # 版本
    DocumentVersionResponse,
    # Chunk
    ChunkResponse,
    ChunkDetailResponse,
    # 索引任务
    IndexTaskResponse,
    IndexRebuildRequest,
    ConsistencyCheckRequest,
)
from app.schemas.qa import (
    StandardQACreate,
    StandardQAUpdate,
    StandardQAPublishRequest,
    StandardQADisableRequest,
    StandardQAResponse,
    StandardQADetailResponse,
    CandidateQAResponse,
    CandidateQAReviewRequest,
    QAMatchRequest,
    QAMatchResponse,
    QAMatchResult,
)

__all__ = [
    # Common
    "BaseSchema",
    "PaginationParams",
    "SortParams",
    "FilterParams",
    "ListResponse",
    "BulkOperationResult",
    "HealthCheckResponse",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserResponse",
    "UserDetailResponse",
    "RoleResponse",
    "PermissionResponse",
    "AccessTokenPayload",
    # Document
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "KnowledgeBaseResponse",
    "KnowledgeBaseDetailResponse",
    "KnowledgeBaseStatsResponse",
    "KnowledgeBasePermissionCreate",
    "KnowledgeBasePermissionResponse",
    "DocumentUploadResponse",
    "DocumentResponse",
    "DocumentDetailResponse",
    "DocumentVersionResponse",
    "ChunkResponse",
    "ChunkDetailResponse",
    "IndexTaskResponse",
    "IndexRebuildRequest",
    "ConsistencyCheckRequest",
    # QA
    "StandardQACreate",
    "StandardQAUpdate",
    "StandardQAPublishRequest",
    "StandardQADisableRequest",
    "StandardQAResponse",
    "StandardQADetailResponse",
    "CandidateQAResponse",
    "CandidateQAReviewRequest",
    "QAMatchRequest",
    "QAMatchResponse",
    "QAMatchResult",
]
