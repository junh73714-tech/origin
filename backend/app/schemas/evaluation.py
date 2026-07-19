"""
评估模块 Schema（成员7）
包含 Golden Dataset、评估用例、评估运行、评估结果等 Schema
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BaseSchema, PaginationParams


# ============================================================================
# Golden Dataset Schema
# ============================================================================

class GoldenDatasetCreate(BaseSchema):
    """创建 Golden Dataset"""
    name: str = Field(..., min_length=1, max_length=255, description="数据集名称")
    description: str | None = Field(default=None, description="数据集描述")
    applicable_config: dict | None = Field(default=None, description="适用配置")
    change_summary: str | None = Field(default=None, description="变更说明")


class GoldenDatasetUpdate(BaseSchema):
    """更新 Golden Dataset"""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    applicable_config: dict | None = None
    status: str | None = Field(default=None, description="状态：draft / active / archived")


class GoldenDatasetResponse(BaseSchema):
    """Golden Dataset 响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    version: int
    status: str
    case_count: int
    applicable_config: dict | None = None
    change_summary: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str


class GoldenDatasetVersionResponse(BaseSchema):
    """Golden Dataset 版本响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    version: int
    change_summary: str | None = None
    case_count: int
    applicable_config: dict | None = None
    created_at: datetime
    created_by: str


# ============================================================================
# 评估用例 Schema
# ============================================================================

class EvalCaseCreate(BaseSchema):
    """创建评估用例"""
    question: str = Field(..., min_length=1, description="标准问题")
    standard_answer: str = Field(..., min_length=1, description="标准答案")
    standard_document_id: str | None = Field(default=None, description="标准文档 ID")
    standard_chunk_id: str | None = Field(default=None, description="标准 Chunk ID")
    allowed_roles: list[str] | None = Field(default=None, description="允许角色")
    forbidden_roles: list[str] | None = Field(default=None, description="禁止角色")
    allowed_departments: list[str] | None = Field(default=None, description="允许部门")
    should_refuse: bool = Field(default=False, description="是否应拒答")
    question_type: str = Field(default="factual", description="问题类型")
    difficulty: str = Field(default="medium", description="难度等级")
    core_entities: list[str] | None = Field(default=None, description="核心实体")
    time_conditions: str | None = Field(default=None, description="时间条件")
    location_conditions: str | None = Field(default=None, description="地区条件")
    tags: list[str] | None = Field(default=None, description="标签")
    weight: float = Field(default=1.0, ge=0.0, description="权重")


class EvalCaseUpdate(BaseSchema):
    """更新评估用例"""
    question: str | None = None
    standard_answer: str | None = None
    standard_document_id: str | None = None
    standard_chunk_id: str | None = None
    allowed_roles: list[str] | None = None
    forbidden_roles: list[str] | None = None
    allowed_departments: list[str] | None = None
    should_refuse: bool | None = None
    question_type: str | None = None
    difficulty: str | None = None
    core_entities: list[str] | None = None
    time_conditions: str | None = None
    location_conditions: str | None = None
    tags: list[str] | None = None
    weight: float | None = None
    is_active: bool | None = None


class EvalCaseResponse(BaseSchema):
    """评估用例响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    question: str
    standard_answer: str
    standard_document_id: str | None = None
    standard_chunk_id: str | None = None
    allowed_roles: list | None = None
    forbidden_roles: list | None = None
    allowed_departments: list | None = None
    should_refuse: bool
    question_type: str
    difficulty: str
    core_entities: list | None = None
    time_conditions: str | None = None
    location_conditions: str | None = None
    tags: list | None = None
    weight: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EvalCaseBatchCreate(BaseSchema):
    """批量创建评估用例"""
    cases: list[EvalCaseCreate] = Field(..., min_length=1, max_length=500, description="用例列表")


# ============================================================================
# 评估运行 Schema
# ============================================================================

class EvalRunCreate(BaseSchema):
    """创建评估运行"""
    dataset_id: str = Field(..., description="数据集 ID")
    access_context: dict | None = Field(default=None, description="测试用的 AccessContext")
    retrieval_config: dict | None = Field(default=None, description="检索参数配置")
    model_version: str | None = Field(default=None, description="模型版本")
    prompt_version: str | None = Field(default=None, description="提示词版本")
    code_version: str | None = Field(default=None, description="代码版本")


class EvalRunResponse(BaseSchema):
    """评估运行响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    dataset_version: int
    status: str
    access_context: dict | None = None
    retrieval_config: dict | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    code_version: str | None = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    skipped_cases: int
    metrics_summary: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class EvalResultResponse(BaseSchema):
    """评估结果响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str
    status: str
    # 检索指标
    recall_at_k: float | None = None
    precision_at_k: float | None = None
    mrr: float | None = None
    ndcg: float | None = None
    standard_doc_hit: bool | None = None
    standard_chunk_hit: bool | None = None
    keyword_recall: float | None = None
    vector_recall: float | None = None
    hybrid_boost: float | None = None
    reranker_boost: float | None = None
    # 生成指标
    faithfulness: float | None = None
    answer_relevance: float | None = None
    context_relevance: float | None = None
    citation_accuracy: float | None = None
    citation_completeness: float | None = None
    no_answer_detection: bool | None = None
    false_refusal: bool | None = None
    hallucination_rate: float | None = None
    # 权限指标
    unauthorized_recall: bool | None = None
    unauthorized_citation: bool | None = None
    unauthorized_answer: bool | None = None
    cross_permission_leak: bool | None = None
    offline_doc_hit: bool | None = None
    expired_doc_hit: bool | None = None
    # 详细信息
    actual_output: str | None = None
    expected_output: str | None = None
    error_message: str | None = None
    execution_time_ms: float | None = None
    created_at: datetime


# ============================================================================
# 查询参数
# ============================================================================

class DatasetQueryParams(PaginationParams):
    """数据集查询参数"""
    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="状态筛选")
    sort_by: str = Field(default="updated_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")


class EvalCaseQueryParams(PaginationParams):
    """评估用例查询参数"""
    dataset_id: str = Field(..., description="数据集 ID")
    question_type: str | None = Field(default=None, description="问题类型")
    difficulty: str | None = Field(default=None, description="难度等级")
    is_active: bool | None = Field(default=None, description="是否启用")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")


class EvalRunQueryParams(PaginationParams):
    """评估运行查询参数"""
    dataset_id: str | None = Field(default=None, description="数据集 ID")
    status: str | None = Field(default=None, description="状态筛选")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")