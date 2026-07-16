"""
标准问答相关 Schema（成员7）
包含标准问答、候选问答、审核、质量检查、匹配等完整 Schema 定义
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import BaseSchema, PaginationParams


# ============================================================================
# 标准问答状态常量
# ============================================================================

class QAStatusEnum:
    """标准问答状态枚举"""
    DRAFT = "draft"
    AUTO_GENERATED = "auto_generated"
    PENDING_REVIEW = "pending_review"
    REVIEW_REJECTED = "review_rejected"
    PENDING_PUBLISH = "pending_publish"
    PUBLISHED = "published"
    PENDING_REVIEW_AGAIN = "pending_review_again"
    EXPIRED = "expired"
    DISABLED = "disabled"


class ReviewActionEnum:
    """审核动作枚举"""
    APPROVE = "approve"
    REJECT = "reject"
    RETURN_FOR_MODIFICATION = "return_for_modification"
    PUBLISH = "publish"
    SUSPEND = "suspend"
    DISABLE = "disable"
    MARK_DUPLICATE = "mark_duplicate"
    MARK_SOURCE_ISSUE = "mark_source_issue"


# ============================================================================
# 问题变体 Schema
# ============================================================================

class QuestionVariantCreate(BaseSchema):
    """创建问题变体"""
    variant_text: str = Field(..., min_length=1, description="变体问句文本")
    variant_type: str = Field(default="manual", description="变体类型：manual / auto_generated")


class QuestionVariantResponse(BaseSchema):
    """问题变体响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    standard_qa_id: str
    variant_text: str
    variant_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# 问答来源绑定 Schema
# ============================================================================

class QASourceCreate(BaseSchema):
    """创建问答来源绑定"""
    document_id: str = Field(..., description="来源文档 ID")
    document_version: int = Field(..., description="来源文档版本号")
    chunk_id: str = Field(..., description="来源 Chunk ID")
    knowledge_base_id: str = Field(..., description="来源知识库 ID")
    is_primary: bool = Field(default=False, description="是否为主要来源")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="相关性评分")
    quote_text: str | None = Field(default=None, description="引用原文片段")


class QASourceResponse(BaseSchema):
    """问答来源绑定响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    qa_id: str
    document_id: str
    document_version: int
    chunk_id: str
    knowledge_base_id: str
    is_primary: bool
    relevance_score: float
    quote_text: str | None = None
    created_at: datetime


# ============================================================================
# 标准问答 Schema
# ============================================================================

class StandardQACreate(BaseSchema):
    """创建标准问答"""
    knowledge_base_id: str = Field(..., description="知识库 ID")
    question: str = Field(..., min_length=1, max_length=2000, description="标准问题")
    short_answer: str | None = Field(default=None, max_length=500, description="简短答案")
    detailed_answer: str | None = Field(default=None, description="详细答案")
    answer: str = Field(..., min_length=1, description="标准答案（完整版）")
    keywords: list[str] | None = Field(default=None, description="关键词列表")
    core_entities: list[str] | None = Field(default=None, description="核心实体列表")
    category: str | None = Field(default=None, max_length=100, description="分类")
    applicable_roles: list[str] | None = Field(default=None, description="适用角色列表")
    applicable_departments: list[str] | None = Field(default=None, description="适用部门列表")
    access_scope: dict | None = Field(default=None, description="访问范围约束")
    priority: int = Field(default=0, ge=0, description="优先级")
    effective_start: datetime | None = Field(default=None, description="生效开始时间")
    effective_end: datetime | None = Field(default=None, description="生效结束时间")
    sources: list[QASourceCreate] = Field(default_factory=list, description="来源绑定列表")
    variants: list[QuestionVariantCreate] = Field(default_factory=list, description="问题变体列表")
    metadata: dict | None = Field(default=None, description="扩展元数据")


class StandardQAUpdate(BaseSchema):
    """更新标准问答"""
    question: str | None = Field(default=None, min_length=1, max_length=2000)
    short_answer: str | None = Field(default=None, max_length=500)
    detailed_answer: str | None = None
    answer: str | None = Field(default=None, min_length=1)
    keywords: list[str] | None = None
    core_entities: list[str] | None = None
    category: str | None = Field(default=None, max_length=100)
    applicable_roles: list[str] | None = None
    applicable_departments: list[str] | None = None
    access_scope: dict | None = None
    priority: int | None = Field(default=None, ge=0)
    effective_start: datetime | None = None
    effective_end: datetime | None = None
    metadata: dict | None = None


class StandardQAResponse(BaseSchema):
    """标准问答列表响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    short_answer: str | None = None
    answer: str
    keywords: list | None = None
    core_entities: list | None = None
    category: str | None = None
    knowledge_base_id: str
    applicable_roles: list | None = None
    applicable_departments: list | None = None
    access_scope: dict | None = None
    source_document_id: str | None = None
    source_document_version: int | None = None
    source_chunk_id: str | None = None
    status: str
    version: int
    priority: int
    effective_start: datetime | None = None
    effective_end: datetime | None = None
    published_at: datetime | None = None
    expired_at: datetime | None = None
    is_machine_generated: bool = False
    generation_model: str | None = None
    generation_prompt_version: str | None = None
    duplicate_of_id: str | None = None
    view_count: int = 0
    use_count: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: str


class StandardQADetailResponse(StandardQAResponse):
    """标准问答详情响应"""
    detailed_answer: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    sources: list[QASourceResponse] = []
    variants: list[QuestionVariantResponse] = []
    audit_records: list["QAReviewRecordResponse"] = []


class StandardQAPublishRequest(BaseSchema):
    """发布标准问答请求"""
    effective_start: datetime | None = Field(default=None, description="生效开始时间")
    effective_end: datetime | None = Field(default=None, description="生效结束时间")


class StandardQADisableRequest(BaseSchema):
    """停用标准问答请求"""
    reason: str = Field(..., min_length=1, description="停用原因")


# ============================================================================
# 候选问答 Schema
# ============================================================================

class CandidateQAGenerateRequest(BaseSchema):
    """触发候选问答生成任务请求"""
    knowledge_base_id: str = Field(..., description="知识库 ID")
    document_ids: list[str] | None = Field(default=None, description="指定文档 ID 列表，为空则处理全部有效文档")
    chunk_ids: list[str] | None = Field(default=None, description="指定 Chunk ID 列表")
    max_candidates: int = Field(default=50, ge=1, le=500, description="最大生成候选数")
    model: str | None = Field(default=None, description="指定生成模型")
    prompt_version: str | None = Field(default=None, description="指定提示词版本")


class CandidateQAResponse(BaseSchema):
    """候选问答列表响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    standard_qa_id: str | None = None
    knowledge_base_id: str
    question: str
    short_answer: str | None = None
    detailed_answer: str | None = None
    answer: str
    variants: list | None = None
    keywords: list | None = None
    core_entities: list | None = None
    suggested_roles: list | None = None
    suggested_departments: list | None = None
    source_document_ids: list | None = None
    source_chunk_ids: list | None = None
    source: str
    source_session_id: str | None = None
    generation_model: str | None = None
    generation_prompt_version: str | None = None
    confidence: float | None = None
    status: str
    review_comment: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    duplicate_of_id: str | None = None
    duplicate_of_standard_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CandidateQAReviewRequest(BaseSchema):
    """审核候选问答请求"""
    action: str = Field(
        ...,
        description="审核动作：approve / reject / return_for_modification / mark_duplicate",
    )
    comment: str | None = Field(default=None, description="审核意见")
    duplicate_of_standard_id: str | None = Field(default=None, description="标记为重复时指定目标标准问答 ID")


class CandidateQABatchReviewRequest(BaseSchema):
    """批量审核候选问答请求"""
    candidate_ids: list[str] = Field(..., min_length=1, max_length=100, description="候选问答 ID 列表")
    action: str = Field(..., description="审核动作")
    comment: str | None = Field(default=None, description="审核意见")


# ============================================================================
# 审核记录 Schema
# ============================================================================

class QAReviewRecordCreate(BaseSchema):
    """创建审核记录"""
    qa_id: str = Field(..., description="标准问答 ID")
    action: str = Field(..., description="审核动作")
    comment: str | None = Field(default=None, description="审核意见")
    review_details: dict | None = Field(default=None, description="审核详情")


class QAReviewRecordResponse(BaseSchema):
    """审核记录响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    qa_id: str
    action: str
    status_from: str | None = None
    status_to: str | None = None
    comment: str | None = None
    reviewer_id: str
    reviewer_name: str | None = None
    review_time: datetime
    review_details: dict | None = None
    created_at: datetime


class QAReviewSubmitRequest(BaseSchema):
    """提交审核请求"""
    qa_id: str = Field(..., description="标准问答 ID")
    action: str = Field(
        ...,
        description="审核动作：approve / reject / return_for_modification / publish / "
                    "suspend / disable / mark_duplicate / mark_source_issue",
    )
    comment: str | None = Field(default=None, description="审核意见")
    review_details: dict | None = Field(default=None, description="审核详情")


# ============================================================================
# 质量检查 Schema
# ============================================================================

class QAQualityCheckResponse(BaseSchema):
    """质量检查结果响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    qa_id: str
    candidate_qa_id: str | None = None
    check_name: str
    check_result: bool
    check_score: float | None = None
    check_detail: str | None = None
    is_blocking: bool
    checked_at: datetime
    checker_version: str | None = None


class QAQualityCheckSummary(BaseSchema):
    """质量检查汇总"""
    qa_id: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    blocking_failures: int
    overall_pass: bool
    checks: list[QAQualityCheckResponse] = []


# ============================================================================
# 标准问答匹配 Schema（供成员6调用）
# ============================================================================

class QAMatchRequest(BaseSchema):
    """标准问答匹配请求"""
    query: str = Field(..., min_length=1, description="用户问题")
    keywords: list[str] = Field(default_factory=list, description="关键词")
    entities: list[str] = Field(default_factory=list, description="核心实体")
    intent: str = Field(default="", description="意图")
    access_context: dict = Field(
        default_factory=dict,
        description="来自成员4的权限上下文，包含 roles、departments、permissions、data_scopes",
    )
    knowledge_base_ids: list[str] = Field(default_factory=list, description="知识库 ID 列表")
    top_k: int = Field(default=5, ge=1, le=20, description="返回候选数量")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="综合评分阈值")


class QAMatchResult(BaseSchema):
    """标准问答匹配结果"""
    matched: bool = Field(default=False, description="是否匹配成功")
    qa_id: str = Field(default="", description="标准问答 ID")
    question: str = Field(default="", description="标准问题")
    answer: str = Field(default="", description="标准答案")
    short_answer: str | None = Field(default=None, description="简短答案")
    detailed_answer: str | None = Field(default=None, description="详细答案")
    variants: list[str] = Field(default_factory=list, description="匹配到的相似问法")
    semantic_score: float = Field(default=0.0, description="语义相似度评分")
    keyword_score: float = Field(default=0.0, description="关键词匹配评分")
    entity_consistency: float = Field(default=0.0, description="实体一致性评分")
    scope_consistency: float = Field(default=0.0, description="适用范围一致性评分")
    final_score: float = Field(default=0.0, description="综合评分")
    citations: list[dict] = Field(default_factory=list, description="引用来源")
    status: str = Field(default="", description="匹配状态")
    reason: str = Field(default="", description="匹配说明")


class QAMatchResponse(BaseSchema):
    """标准问答匹配响应"""
    matched: bool = False
    results: list[QAMatchResult] = Field(default_factory=list, description="匹配结果列表")
    query: str = ""
    processing_time_ms: float = 0.0


# ============================================================================
# 查询参数
# ============================================================================

class QAQueryParams(PaginationParams):
    """标准问答查询参数"""
    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="状态筛选")
    category: str | None = Field(default=None, description="分类筛选")
    knowledge_base_id: str | None = Field(default=None, description="知识库 ID 筛选")
    is_machine_generated: bool | None = Field(default=None, description="是否机器生成")
    reviewed_by: str | None = Field(default=None, description="审核人筛选")
    sort_by: str = Field(default="updated_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")


class CandidateQAQueryParams(PaginationParams):
    """候选问答查询参数"""
    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="状态筛选")
    knowledge_base_id: str | None = Field(default=None, description="知识库 ID 筛选")
    source: str | None = Field(default=None, description="来源筛选")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")


class ReviewQueryParams(PaginationParams):
    """审核记录查询参数"""
    qa_id: str | None = Field(default=None, description="标准问答 ID 筛选")
    action: str | None = Field(default=None, description="审核动作筛选")
    reviewer_id: str | None = Field(default=None, description="审核人筛选")
    sort_by: str = Field(default="review_time", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")


# ============================================================================
# 文档版本联动相关 Schema
# ============================================================================

class DocumentVersionChangeEvent(BaseSchema):
    """文档版本变更事件"""
    event_type: str = Field(..., description="事件类型")
    document_id: str = Field(..., description="文档 ID")
    document_version: int | None = Field(default=None, description="文档版本")
    knowledge_base_id: str | None = Field(default=None, description="知识库 ID")
    payload: dict = Field(default_factory=dict, description="事件负载")


class AffectedQAResponse(BaseSchema):
    """受影响的问答响应"""
    qa_id: str
    question: str
    current_status: str
    new_status: str
    reason: str
    document_id: str
    document_version: int


# Forward references 更新
StandardQADetailResponse.model_rebuild()