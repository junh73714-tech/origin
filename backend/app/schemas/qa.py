"""
问答相关 Schema
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BaseSchema


# ============ 标准问答 Schema ============

class StandardQACreate(BaseSchema):
    """创建标准问答"""
    knowledge_base_id: str = Field(..., description="知识库 ID")
    question: str = Field(..., min_length=1, description="问题")
    answer: str = Field(..., min_length=1, description="答案")
    keywords: list[str] | None = Field(default=None, description="关键词")
    category: str | None = Field(default=None, description="分类")
    priority: int = Field(default=0, description="优先级")
    metadata: dict | None = Field(default=None, description="元数据")


class StandardQAUpdate(BaseSchema):
    """更新标准问答"""
    question: str | None = None
    answer: str | None = None
    keywords: list[str] | None = None
    category: str | None = None
    priority: int | None = None
    metadata: dict | None = None


class StandardQAPublish(BaseSchema):
    """发布标准问答"""
    pass


class StandardQAUnpublish(BaseSchema):
    """下线标准问答"""
    reason: str | None = Field(default=None, description="下线原因")


class StandardQAResponse(BaseSchema):
    """标准问答响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    question: str
    answer: str
    keywords: list[str] | None = None
    category: str | None = None
    status: str
    priority: int
    view_count: int
    use_count: int
    metadata: dict | None = None
    published_at: datetime | None = None
    expired_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StandardQADetailResponse(StandardQAResponse):
    """标准问答详情"""
    references: list["QaReferenceResponse"] = []
    audit_records: list["QaAuditRecordResponse"] = []


# ============ 候选问答 Schema ============

class CandidateQACreate(BaseSchema):
    """创建候选问答"""
    knowledge_base_id: str
    question: str
    answer: str
    source: str  # ai_generate, user_submit, import


class CandidateQAResponse(BaseSchema):
    """候选问答响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    standard_qa_id: str | None = None
    knowledge_base_id: str
    question: str
    answer: str
    source: str
    source_session_id: str | None = None
    confidence: float | None = None
    status: str
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class CandidateQAReview(BaseSchema):
    """审核候选问答"""
    action: str = Field(..., description="审核动作: approve, reject")
    comment: str | None = Field(default=None, description="审核意见")


# ============ 引用 Schema ============

class QaReferenceResponse(BaseSchema):
    """问答引用响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    qa_id: str
    document_id: str
    chunk_id: str
    relevance_score: float
    quote_text: str | None = None


# ============ 审核记录 Schema ============

class QaAuditRecordResponse(BaseSchema):
    """问答审核记录响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    qa_id: str
    action: str
    status_from: str | None = None
    status_to: str | None = None
    comment: str | None = None
    created_by: str
    created_at: datetime


# ============ 会话 Schema ============

class ConversationCreate(BaseSchema):
    """创建会话"""
    session_id: str | None = None
    title: str | None = None
    metadata: dict | None = None


class ConversationResponse(BaseSchema):
    """会话响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    session_id: str | None = None
    title: str | None = None
    status: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseSchema):
    """消息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    intent: str | None = None
    matched_qa_id: str | None = None
    confidence: float | None = None
    references: list[dict] | None = None
    feedback: str | None = None
    feedback_comment: str | None = None
    created_at: datetime


class MessageCreate(BaseSchema):
    """发送消息"""
    conversation_id: str | None = None
    content: str = Field(..., min_length=1)
    metadata: dict | None = None


# ============ 反馈 Schema ============

class FeedbackCreate(BaseSchema):
    """创建反馈"""
    message_id: str
    feedback: str = Field(..., pattern="^(positive|negative)$")
    comment: str | None = None
    score: int | None = Field(default=None, ge=1, le=5)


class FeedbackResponse(BaseSchema):
    """反馈响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    feedback: str
    comment: str | None = None
    score: int | None = None
    created_at: datetime


# Forward references
StandardQADetailResponse.model_rebuild()
