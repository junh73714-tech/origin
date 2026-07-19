"""
标准问答相关模型
包括标准问答、候选问答、问题变体、来源绑定、审核记录、质量检查等
成员7负责：标准问答生命周期、审核发布状态机、候选问答生成
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


# ============================================================================
# 标准问答状态常量
# ============================================================================

class QAStatus:
    """标准问答状态枚举"""

    DRAFT = "draft"                       # 草稿
    AUTO_GENERATED = "auto_generated"     # 自动生成（待人工处理）
    PENDING_REVIEW = "pending_review"     # 待审核
    REVIEW_REJECTED = "review_rejected"   # 审核驳回
    PENDING_PUBLISH = "pending_publish"   # 待发布
    PUBLISHED = "published"               # 已发布
    PENDING_REVIEW_AGAIN = "pending_review_again"  # 待复核（来源文档变更触发）
    EXPIRED = "expired"                   # 已过期
    DISABLED = "disabled"                 # 已停用


class ReviewAction:
    """审核动作枚举"""

    APPROVE = "approve"                 # 通过
    REJECT = "reject"                   # 驳回
    RETURN_FOR_MODIFICATION = "return_for_modification"  # 返回修改
    PUBLISH = "publish"                 # 发布
    SUSPEND = "suspend"                 # 暂停
    DISABLE = "disable"                 # 停用
    MARK_DUPLICATE = "mark_duplicate"   # 标记重复
    MARK_SOURCE_ISSUE = "mark_source_issue"  # 标记来源文档问题


# 状态流转映射
QA_STATUS_TRANSITIONS: dict[str, list[str]] = {
    QAStatus.DRAFT: [QAStatus.AUTO_GENERATED, QAStatus.PENDING_REVIEW],
    QAStatus.AUTO_GENERATED: [QAStatus.PENDING_REVIEW, QAStatus.DRAFT],
    QAStatus.PENDING_REVIEW: [
        QAStatus.PENDING_PUBLISH,
        QAStatus.REVIEW_REJECTED,
        QAStatus.DRAFT,
    ],
    QAStatus.REVIEW_REJECTED: [QAStatus.PENDING_REVIEW, QAStatus.DRAFT],
    QAStatus.PENDING_PUBLISH: [QAStatus.PUBLISHED, QAStatus.PENDING_REVIEW],
    QAStatus.PUBLISHED: [
        QAStatus.PENDING_REVIEW_AGAIN,
        QAStatus.EXPIRED,
        QAStatus.DISABLED,
    ],
    QAStatus.PENDING_REVIEW_AGAIN: [
        QAStatus.PENDING_REVIEW,
        QAStatus.PUBLISHED,
        QAStatus.DISABLED,
    ],
    QAStatus.EXPIRED: [QAStatus.PENDING_REVIEW],
    QAStatus.DISABLED: [QAStatus.PENDING_REVIEW],
}


# ============================================================================
# 标准问答模型（增强版）
# ============================================================================

class StandardQA(BaseModel):
    """
    标准问答模型
    每个标准问答绑定来源文档、版本、Chunk、适用知识库、角色、部门、
    生效时间、失效时间、审核人、审核时间、状态、版本
    """

    __tablename__ = "standard_qas"

    # === 基础内容 ===
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="标准问题")
    short_answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简短答案")
    detailed_answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="详细答案")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="标准答案（完整版）")

    # === 检索与匹配 ===
    keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="关键词列表")
    core_entities: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="核心实体列表")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True, comment="分类")

    # === 适用范围 ===
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )
    applicable_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="适用角色列表")
    applicable_departments: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="适用部门列表")
    # 标准问答不得拥有比来源文档更大的访问范围
    access_scope: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="访问范围约束")

    # === 来源绑定 ===
    source_document_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="来源文档",
    )
    source_document_version: Mapped[int | None] = mapped_column(nullable=True, comment="来源文档版本")
    source_chunk_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        comment="来源 Chunk",
    )

    # === 生命周期 ===
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=QAStatus.DRAFT,
        index=True,
        comment="状态",
    )
    version: Mapped[int] = mapped_column(default=1, nullable=False, comment="问答版本号")
    priority: Mapped[int] = mapped_column(default=0, nullable=False, comment="优先级")
    effective_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="生效开始时间"
    )
    effective_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="生效结束时间"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布时间"
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="过期时间"
    )

    # === 审核信息 ===
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="审核人 ID")
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审核时间"
    )

    # === 生成信息 ===
    is_machine_generated: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="是否为机器生成"
    )
    generation_model: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="生成模型名称")
    generation_prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="提示词版本号")

    # === 重复检测 ===
    duplicate_of_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="SET NULL"),
        nullable=True,
        comment="标记为重复的目标问答 ID",
    )

    # === 统计 ===
    view_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="查看次数")
    use_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="命中次数")
    positive_feedback_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="正向反馈次数")
    negative_feedback_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="负向反馈次数")

    # === 扩展元数据 ===
    qa_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, comment="扩展元数据")

    # === 关系 ===
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")
    source_document: Mapped["Document | None"] = relationship(
        "Document", foreign_keys=[source_document_id]
    )
    source_chunk: Mapped["DocumentChunk | None"] = relationship(
        "DocumentChunk", foreign_keys=[source_chunk_id]
    )
    variants: Mapped[list["QuestionVariant"]] = relationship(
        "QuestionVariant", back_populates="standard_qa", cascade="all, delete-orphan"
    )
    sources: Mapped[list["QASource"]] = relationship(
        "QASource", back_populates="qa", cascade="all, delete-orphan"
    )
    audit_records: Mapped[list["QAReviewRecord"]] = relationship(
        "QAReviewRecord", back_populates="qa", cascade="all, delete-orphan"
    )
    quality_checks: Mapped[list["QAQualityCheck"]] = relationship(
        "QAQualityCheck", back_populates="qa", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_standard_qas_status_category", "status", "category"),
        Index("ix_standard_qas_kb_status", "knowledge_base_id", "status"),
        Index("ix_standard_qas_source_doc", "source_document_id", "source_document_version"),
        Index("ix_standard_qas_effective", "effective_start", "effective_end"),
        Index("ix_standard_qas_duplicate", "duplicate_of_id"),
    )

    def __repr__(self) -> str:
        return f"<StandardQA {self.id} v{self.version} [{self.status}]>"


# ============================================================================
# 问题变体模型
# ============================================================================

class QuestionVariant(BaseModel):
    """
    相似问法模型
    一个标准问题可以有多个相似问法，用于提升匹配召回率
    """

    __tablename__ = "question_variants"

    standard_qa_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属标准问答",
    )
    variant_text: Mapped[str] = mapped_column(Text, nullable=False, comment="变体问句文本")
    variant_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        comment="变体类型：manual（人工）/ auto_generated（自动生成）",
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, comment="是否启用")
    generation_model: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="生成模型")

    # === 关系 ===
    standard_qa: Mapped["StandardQA"] = relationship("StandardQA", back_populates="variants")

    __table_args__ = (
        Index("ix_question_variants_qa", "standard_qa_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<QuestionVariant {self.id} [{self.variant_type}]>"


# ============================================================================
# 问答来源绑定模型
# ============================================================================

class QASource(BaseModel):
    """
    问答来源绑定模型
    绑定标准问答到具体的来源文档、版本、Chunk、知识库
    """

    __tablename__ = "qa_sources"

    qa_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属标准问答",
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="来源文档",
    )
    document_version: Mapped[int] = mapped_column(nullable=False, comment="来源文档版本号")
    chunk_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        comment="来源 Chunk",
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        comment="来源知识库",
    )
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否为主要来源")
    relevance_score: Mapped[float] = mapped_column(default=1.0, nullable=False, comment="相关性评分")
    quote_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="引用原文片段")

    # === 关系 ===
    qa: Mapped["StandardQA"] = relationship("StandardQA", back_populates="sources")
    document: Mapped["Document"] = relationship("Document")
    chunk: Mapped["DocumentChunk"] = relationship("DocumentChunk")

    __table_args__ = (
        Index("ix_qa_sources_qa_doc", "qa_id", "document_id"),
        Index("ix_qa_sources_doc_version", "document_id", "document_version"),
    )

    def __repr__(self) -> str:
        return f"<QASource {self.qa_id} -> doc:{self.document_id} v{self.document_version}>"


# ============================================================================
# 候选问答模型（增强版）
# ============================================================================

class CandidateQA(BaseModel):
    """
    候选问答模型（待审核）
    由 Celery 异步任务生成，消费成员5提供的有效文档和 Chunk
    """

    __tablename__ = "candidate_qas"

    # === 关联 ===
    standard_qa_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联的标准问答（发布后回填）",
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属知识库",
    )

    # === 内容 ===
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="候选问题")
    short_answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简短答案")
    detailed_answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="详细答案")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="完整答案")

    # === 相似问法 ===
    variants: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="自动生成的相似问法列表")

    # === 检索标签 ===
    keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="关键词")
    core_entities: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="核心实体")

    # === 适用范围建议 ===
    suggested_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="建议适用角色")
    suggested_departments: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="建议适用部门")

    # === 来源绑定 ===
    source_document_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="来源文档 ID 列表")
    source_chunk_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="来源 Chunk ID 列表")

    # === 生成信息 ===
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ai_generate", comment="来源：ai_generate / user_submit / import"
    )
    source_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="生成任务会话 ID")
    generation_model: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="生成模型名称")
    generation_prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="提示词版本号")
    confidence: Mapped[float | None] = mapped_column(nullable=True, comment="生成置信度")

    # === 审核状态 ===
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True,
        comment="状态：pending / approved / rejected / duplicate",
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="审核人")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审核时间")

    # === 重复检测 ===
    duplicate_of_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="重复的目标候选问答 ID"
    )
    duplicate_of_standard_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="重复的已发布标准问答 ID"
    )

    # === 扩展元数据 ===
    qa_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, comment="扩展元数据")

    # === 关系 ===
    standard_qa: Mapped["StandardQA | None"] = relationship("StandardQA")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")

    __table_args__ = (
        Index("ix_candidate_qas_kb_status", "knowledge_base_id", "status"),
        Index("ix_candidate_qas_source", "source", "status"),
    )

    def __repr__(self) -> str:
        return f"<CandidateQA {self.id} [{self.status}]>"


# ============================================================================
# 审核记录模型（增强版）
# ============================================================================

class QAReviewRecord(BaseModel):
    """
    问答审核记录模型
    记录每次审核动作的详细信息
    """

    __tablename__ = "qa_review_records"

    qa_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属标准问答",
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="审核动作",
    )
    status_from: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="审核前状态")
    status_to: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="审核后状态")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    reviewer_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="审核人 ID")
    reviewer_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="审核人姓名")
    review_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="审核时间"
    )
    review_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="审核详情")

    # === 关系 ===
    qa: Mapped["StandardQA"] = relationship("StandardQA", back_populates="audit_records")

    __table_args__ = (
        Index("ix_qa_review_records_qa_time", "qa_id", "review_time"),
        Index("ix_qa_review_records_reviewer", "reviewer_id", "review_time"),
    )

    def __repr__(self) -> str:
        return f"<QAReviewRecord {self.qa_id} {self.action}>"


# ============================================================================
# 质量检查结果模型
# ============================================================================

class QAQualityCheck(BaseModel):
    """
    质量检查结果模型
    自动质量检查，辅助审核但不替代人工审核
    """

    __tablename__ = "qa_quality_checks"

    qa_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属标准问答",
    )
    candidate_qa_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("candidate_qas.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的候选问答",
    )

    # === 检查项结果 ===
    check_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="检查项名称")
    check_result: Mapped[bool] = mapped_column(nullable=False, comment="检查结果：通过/未通过")
    check_score: Mapped[float | None] = mapped_column(nullable=True, comment="检查评分")
    check_detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="检查详情")
    is_blocking: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否为阻断性检查")

    # === 检查时间 ===
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="检查时间"
    )
    checker_version: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="检查器版本")

    # === 关系 ===
    qa: Mapped["StandardQA"] = relationship("StandardQA", back_populates="quality_checks")
    candidate_qa: Mapped["CandidateQA | None"] = relationship("CandidateQA")

    __table_args__ = (
        Index("ix_qa_quality_checks_qa", "qa_id", "check_name"),
        Index("ix_qa_quality_checks_candidate", "candidate_qa_id"),
    )

    def __repr__(self) -> str:
        return f"<QAQualityCheck {self.qa_id} {self.check_name}={self.check_result}>"


# ============================================================================
# 保留旧模型别名（兼容性）
# ============================================================================

QaReference = QASource
QaAuditRecord = QAReviewRecord


# ============================================================================
# 会话与消息模型
# ============================================================================

class Conversation(BaseModel):
    """会话模型"""

    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    conv_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # 关系
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", order_by="Message.created_at"
    )

    __table_args__ = (
        Index("ix_conversations_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id}>"


class Message(BaseModel):
    """消息模型"""

    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    matched_qa_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="SET NULL"),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    references: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(50), nullable=True)  # positive, negative
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    msg_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # 关系
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} [{self.role}]>"


class UserFeedback(BaseModel):
    """用户反馈模型"""

    __tablename__ = "user_feedbacks"

    message_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qa_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联的标准问答",
    )
    feedback_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="反馈类型：positive / negative / correction",
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="反馈说明")
    correction_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="纠错内容")
    score: Mapped[int | None] = mapped_column(nullable=True, comment="1-5 评分")
    is_resolved: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否已处理")
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="处理人")
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="处理时间"
    )

    # 关系
    message: Mapped["Message"] = relationship("Message")

    __table_args__ = (
        Index("ix_user_feedbacks_type_resolved", "feedback_type", "is_resolved"),
        Index("ix_user_feedbacks_qa", "qa_id", "feedback_type"),
    )

    def __repr__(self) -> str:
        return f"<UserFeedback {self.message_id} {self.feedback_type}>"


# 延迟导入避免循环引用
from app.models.document import Document, DocumentChunk, KnowledgeBase