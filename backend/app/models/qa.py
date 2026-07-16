"""
问答相关模型
包括问答对、问答会话、引用等
"""
from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class StandardQA(BaseModel):
    """标准问答模型"""

    __tablename__ = "standard_qas"

    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(default=0, nullable=False)
    use_count: Mapped[int] = mapped_column(default=0, nullable=False)
    qa_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, comment="元数据")
    published_at: Mapped[str | None] = mapped_column(nullable=True)
    expired_at: Mapped[str | None] = mapped_column(nullable=True)

    # 关系
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")
    references: Mapped[list["QaReference"]] = relationship("QaReference", back_populates="qa")
    audit_records: Mapped[list["QaAuditRecord"]] = relationship("QaAuditRecord", back_populates="qa")

    __table_args__ = (
        Index("ix_standard_qas_status_category", "status", "category"),
    )

    def __repr__(self) -> str:
        return f"<StandardQA {self.id} [{self.status}]>"


class CandidateQA(BaseModel):
    """候选问答模型（待审核）"""

    __tablename__ = "candidate_qas"

    standard_qa_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # ai_generate, user_submit, import
    source_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(nullable=True)
    candidate_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, comment="元数据")

    # 关系
    standard_qa: Mapped["StandardQA | None"] = relationship("StandardQA")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")

    def __repr__(self) -> str:
        return f"<CandidateQA {self.id} [{self.status}]>"


class QaReference(BaseModel):
    """问答引用模型"""

    __tablename__ = "qa_references"

    qa_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relevance_score: Mapped[float] = mapped_column(nullable=False)
    quote_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关系
    qa: Mapped["StandardQA"] = relationship("StandardQA", back_populates="references")
    document: Mapped["Document"] = relationship("Document")
    chunk: Mapped["DocumentChunk"] = relationship("DocumentChunk")

    __table_args__ = (
        Index("ix_qa_references_qa_doc", "qa_id", "document_id"),
    )

    def __repr__(self) -> str:
        return f"<QaReference {self.qa_id} -> {self.chunk_id}>"


class QaAuditRecord(BaseModel):
    """问答审核记录模型"""

    __tablename__ = "qa_audit_records"

    qa_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("standard_qas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, update, publish, unpublish, delete
    status_from: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status_to: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关系
    qa: Mapped["StandardQA"] = relationship("StandardQA", back_populates="audit_records")

    def __repr__(self) -> str:
        return f"<QaAuditRecord {self.qa_id} {self.action}>"


class Conversation(BaseModel):
    """会话模型"""

    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    conv_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, comment="元数据")

    # 关系
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", order_by="Message.created_at")

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
    references: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)  # 检索到的引用
    feedback: Mapped[str | None] = mapped_column(String(50), nullable=True)  # positive, negative, null
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    msg_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, comment="元数据")

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
    feedback: Mapped[str] = mapped_column(String(50), nullable=False)  # positive, negative
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int | None] = mapped_column(nullable=True)  # 1-5 评分

    def __repr__(self) -> str:
        return f"<UserFeedback {self.message_id} {self.feedback}>"
