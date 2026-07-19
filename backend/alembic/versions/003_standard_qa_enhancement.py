"""添加标准问答增强模型

Revision ID: 003
Revises: 002
Create Date: 2026-07-16

成员7：添加 question_variants、qa_sources、qa_review_records、qa_quality_checks 表
以及更新 standard_qas、candidate_qas、user_feedbacks 表的新字段
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================================================
    # 1. 创建 question_variants 表（问题变体）
    # ========================================================================
    op.create_table(
        "question_variants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("standard_qa_id", sa.String(64), sa.ForeignKey("standard_qas.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("variant_text", sa.Text(), nullable=False, comment="变体问句文本"),
        sa.Column("variant_type", sa.String(50), nullable=False, server_default="manual", comment="变体类型：manual / auto_generated"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="是否启用"),
        sa.Column("generation_model", sa.String(100), nullable=True, comment="生成模型"),
        # 基础字段
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_question_variants_qa", "question_variants", ["standard_qa_id", "is_active"])

    # ========================================================================
    # 2. 创建 qa_sources 表（问答来源绑定）
    # ========================================================================
    op.create_table(
        "qa_sources",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("qa_id", sa.String(64), sa.ForeignKey("standard_qas.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属标准问答"),
        sa.Column("document_id", sa.String(64), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, comment="来源文档"),
        sa.Column("document_version", sa.Integer(), nullable=False, comment="来源文档版本号"),
        sa.Column("chunk_id", sa.String(64), sa.ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, comment="来源 Chunk"),
        sa.Column("knowledge_base_id", sa.String(64), sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, comment="来源知识库"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否为主要来源"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default=sa.text("1.0"), comment="相关性评分"),
        sa.Column("quote_text", sa.Text(), nullable=True, comment="引用原文片段"),
        # 基础字段
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_qa_sources_qa_doc", "qa_sources", ["qa_id", "document_id"])
    op.create_index("ix_qa_sources_doc_version", "qa_sources", ["document_id", "document_version"])

    # ========================================================================
    # 3. 创建 qa_review_records 表（审核记录）
    # ========================================================================
    op.create_table(
        "qa_review_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("qa_id", sa.String(64), sa.ForeignKey("standard_qas.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属标准问答"),
        sa.Column("action", sa.String(50), nullable=False, comment="审核动作"),
        sa.Column("status_from", sa.String(50), nullable=True, comment="审核前状态"),
        sa.Column("status_to", sa.String(50), nullable=True, comment="审核后状态"),
        sa.Column("comment", sa.Text(), nullable=True, comment="审核意见"),
        sa.Column("reviewer_id", sa.String(64), nullable=False, comment="审核人 ID"),
        sa.Column("reviewer_name", sa.String(100), nullable=True, comment="审核人姓名"),
        sa.Column("review_time", sa.DateTime(timezone=True), nullable=False, comment="审核时间"),
        sa.Column("review_details", postgresql.JSONB(), nullable=True, comment="审核详情"),
        # 基础字段
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_qa_review_records_qa_time", "qa_review_records", ["qa_id", "review_time"])
    op.create_index("ix_qa_review_records_reviewer", "qa_review_records", ["reviewer_id", "review_time"])

    # ========================================================================
    # 4. 创建 qa_quality_checks 表（质量检查结果）
    # ========================================================================
    op.create_table(
        "qa_quality_checks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("qa_id", sa.String(64), sa.ForeignKey("standard_qas.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属标准问答"),
        sa.Column("candidate_qa_id", sa.String(64), sa.ForeignKey("candidate_qas.id", ondelete="SET NULL"), nullable=True, comment="关联的候选问答"),
        sa.Column("check_name", sa.String(100), nullable=False, comment="检查项名称"),
        sa.Column("check_result", sa.Boolean(), nullable=False, comment="检查结果：通过/未通过"),
        sa.Column("check_score", sa.Float(), nullable=True, comment="检查评分"),
        sa.Column("check_detail", sa.Text(), nullable=True, comment="检查详情"),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否为阻断性检查"),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, comment="检查时间"),
        sa.Column("checker_version", sa.String(50), nullable=True, comment="检查器版本"),
        # 基础字段
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_qa_quality_checks_qa", "qa_quality_checks", ["qa_id", "check_name"])
    op.create_index("ix_qa_quality_checks_candidate", "qa_quality_checks", ["candidate_qa_id"])

    # ========================================================================
    # 5. 更新 standard_qas 表（添加新字段）
    # ========================================================================
    op.add_column("standard_qas", sa.Column("short_answer", sa.Text(), nullable=True, comment="简短答案"))
    op.add_column("standard_qas", sa.Column("detailed_answer", sa.Text(), nullable=True, comment="详细答案"))
    op.add_column("standard_qas", sa.Column("core_entities", postgresql.JSONB(), nullable=True, comment="核心实体列表"))
    op.add_column("standard_qas", sa.Column("category", sa.String(100), nullable=True, index=True, comment="分类"))
    op.add_column("standard_qas", sa.Column("applicable_roles", postgresql.JSONB(), nullable=True, comment="适用角色列表"))
    op.add_column("standard_qas", sa.Column("applicable_departments", postgresql.JSONB(), nullable=True, comment="适用部门列表"))
    op.add_column("standard_qas", sa.Column("access_scope", postgresql.JSONB(), nullable=True, comment="访问范围约束"))
    op.add_column("standard_qas", sa.Column("source_chunk_id", sa.String(64), nullable=True, comment="来源 Chunk"))
    op.add_column("standard_qas", sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1"), comment="问答版本号"))
    op.add_column("standard_qas", sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="优先级"))
    op.add_column("standard_qas", sa.Column("effective_start", sa.DateTime(timezone=True), nullable=True, comment="生效开始时间"))
    op.add_column("standard_qas", sa.Column("effective_end", sa.DateTime(timezone=True), nullable=True, comment="生效结束时间"))
    op.add_column("standard_qas", sa.Column("reviewed_by", sa.String(64), nullable=True, comment="审核人 ID"))
    op.add_column("standard_qas", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True, comment="审核时间"))
    op.add_column("standard_qas", sa.Column("is_machine_generated", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否为机器生成"))
    op.add_column("standard_qas", sa.Column("generation_model", sa.String(100), nullable=True, comment="生成模型名称"))
    op.add_column("standard_qas", sa.Column("generation_prompt_version", sa.String(50), nullable=True, comment="提示词版本号"))
    op.add_column("standard_qas", sa.Column("duplicate_of_id", sa.String(64), nullable=True, comment="标记为重复的目标问答 ID"))
    op.add_column("standard_qas", sa.Column("positive_feedback_count", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="正向反馈次数"))
    op.add_column("standard_qas", sa.Column("negative_feedback_count", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="负向反馈次数"))
    op.add_column("standard_qas", sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True, comment="过期时间"))
    op.create_index("ix_standard_qas_status_category", "standard_qas", ["status", "category"])
    op.create_index("ix_standard_qas_kb_status", "standard_qas", ["knowledge_base_id", "status"])
    op.create_index("ix_standard_qas_source_doc", "standard_qas", ["source_document_id", "source_document_version"])
    op.create_index("ix_standard_qas_effective", "standard_qas", ["effective_start", "effective_end"])
    op.create_index("ix_standard_qas_duplicate", "standard_qas", ["duplicate_of_id"])

    # ========================================================================
    # 6. 更新 candidate_qas 表（添加新字段）
    # ========================================================================
    op.add_column("candidate_qas", sa.Column("short_answer", sa.Text(), nullable=True, comment="简短答案"))
    op.add_column("candidate_qas", sa.Column("detailed_answer", sa.Text(), nullable=True, comment="详细答案"))
    op.add_column("candidate_qas", sa.Column("variants", postgresql.JSONB(), nullable=True, comment="自动生成的相似问法列表"))
    op.add_column("candidate_qas", sa.Column("keywords", postgresql.JSONB(), nullable=True, comment="关键词"))
    op.add_column("candidate_qas", sa.Column("core_entities", postgresql.JSONB(), nullable=True, comment="核心实体"))
    op.add_column("candidate_qas", sa.Column("suggested_roles", postgresql.JSONB(), nullable=True, comment="建议适用角色"))
    op.add_column("candidate_qas", sa.Column("suggested_departments", postgresql.JSONB(), nullable=True, comment="建议适用部门"))
    op.add_column("candidate_qas", sa.Column("source_document_ids", postgresql.JSONB(), nullable=True, comment="来源文档 ID 列表"))
    op.add_column("candidate_qas", sa.Column("source_chunk_ids", postgresql.JSONB(), nullable=True, comment="来源 Chunk ID 列表"))
    op.add_column("candidate_qas", sa.Column("generation_model", sa.String(100), nullable=True, comment="生成模型名称"))
    op.add_column("candidate_qas", sa.Column("generation_prompt_version", sa.String(50), nullable=True, comment="提示词版本号"))
    op.add_column("candidate_qas", sa.Column("confidence", sa.Float(), nullable=True, comment="生成置信度"))
    op.add_column("candidate_qas", sa.Column("duplicate_of_standard_id", sa.String(64), nullable=True, comment="重复的已发布标准问答 ID"))
    op.create_index("ix_candidate_qas_kb_status", "candidate_qas", ["knowledge_base_id", "status"])
    op.create_index("ix_candidate_qas_source", "candidate_qas", ["source", "status"])

    # ========================================================================
    # 7. 更新 user_feedbacks 表（添加新字段）
    # ========================================================================
    op.add_column("user_feedbacks", sa.Column("qa_id", sa.String(64), nullable=True, comment="关联的标准问答"))
    op.add_column("user_feedbacks", sa.Column("correction_text", sa.Text(), nullable=True, comment="纠错内容"))
    op.add_column("user_feedbacks", sa.Column("score", sa.Integer(), nullable=True, comment="1-5 评分"))
    op.add_column("user_feedbacks", sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否已处理"))
    op.add_column("user_feedbacks", sa.Column("resolved_by", sa.String(64), nullable=True, comment="处理人"))
    op.add_column("user_feedbacks", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True, comment="处理时间"))
    op.create_index("ix_user_feedbacks_type_resolved", "user_feedbacks", ["feedback_type", "is_resolved"])
    op.create_index("ix_user_feedbacks_qa", "user_feedbacks", ["qa_id", "feedback_type"])


def downgrade() -> None:
    # 删除 user_feedbacks 表的新字段
    op.drop_index("ix_user_feedbacks_qa", table_name="user_feedbacks")
    op.drop_index("ix_user_feedbacks_type_resolved", table_name="user_feedbacks")
    op.drop_column("user_feedbacks", "resolved_at")
    op.drop_column("user_feedbacks", "resolved_by")
    op.drop_column("user_feedbacks", "is_resolved")
    op.drop_column("user_feedbacks", "score")
    op.drop_column("user_feedbacks", "correction_text")
    op.drop_column("user_feedbacks", "qa_id")

    # 删除 candidate_qas 表的新字段
    op.drop_index("ix_candidate_qas_source", table_name="candidate_qas")
    op.drop_index("ix_candidate_qas_kb_status", table_name="candidate_qas")
    op.drop_column("candidate_qas", "duplicate_of_standard_id")
    op.drop_column("candidate_qas", "confidence")
    op.drop_column("candidate_qas", "generation_prompt_version")
    op.drop_column("candidate_qas", "generation_model")
    op.drop_column("candidate_qas", "source_chunk_ids")
    op.drop_column("candidate_qas", "source_document_ids")
    op.drop_column("candidate_qas", "suggested_departments")
    op.drop_column("candidate_qas", "suggested_roles")
    op.drop_column("candidate_qas", "core_entities")
    op.drop_column("candidate_qas", "keywords")
    op.drop_column("candidate_qas", "variants")
    op.drop_column("candidate_qas", "detailed_answer")
    op.drop_column("candidate_qas", "short_answer")

    # 删除 standard_qas 表的新字段
    op.drop_index("ix_standard_qas_duplicate", table_name="standard_qas")
    op.drop_index("ix_standard_qas_effective", table_name="standard_qas")
    op.drop_index("ix_standard_qas_source_doc", table_name="standard_qas")
    op.drop_index("ix_standard_qas_kb_status", table_name="standard_qas")
    op.drop_index("ix_standard_qas_status_category", table_name="standard_qas")
    op.drop_column("standard_qas", "expired_at")
    op.drop_column("standard_qas", "negative_feedback_count")
    op.drop_column("standard_qas", "positive_feedback_count")
    op.drop_column("standard_qas", "duplicate_of_id")
    op.drop_column("standard_qas", "generation_prompt_version")
    op.drop_column("standard_qas", "generation_model")
    op.drop_column("standard_qas", "is_machine_generated")
    op.drop_column("standard_qas", "reviewed_at")
    op.drop_column("standard_qas", "reviewed_by")
    op.drop_column("standard_qas", "effective_end")
    op.drop_column("standard_qas", "effective_start")
    op.drop_column("standard_qas", "priority")
    op.drop_column("standard_qas", "version")
    op.drop_column("standard_qas", "source_chunk_id")
    op.drop_column("standard_qas", "access_scope")
    op.drop_column("standard_qas", "applicable_departments")
    op.drop_column("standard_qas", "applicable_roles")
    op.drop_column("standard_qas", "category")
    op.drop_column("standard_qas", "core_entities")
    op.drop_column("standard_qas", "detailed_answer")
    op.drop_column("standard_qas", "short_answer")

    # 删除新表
    op.drop_table("qa_quality_checks")
    op.drop_table("qa_review_records")
    op.drop_table("qa_sources")
    op.drop_table("question_variants")