"""添加评估模块模型

Revision ID: 004
Revises: 003
Create Date: 2026-07-16

成员7：添加 golden_datasets、golden_dataset_versions、eval_cases、eval_runs、eval_results 表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建 golden_datasets 表
    op.create_table(
        "golden_datasets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, comment="数据集名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="数据集描述"),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1"), comment="数据集版本号"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft", comment="状态"),
        sa.Column("applicable_config", postgresql.JSONB(), nullable=True, comment="适用配置"),
        sa.Column("change_summary", sa.Text(), nullable=True, comment="版本变更说明"),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="用例数量"),
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_golden_datasets_status", "golden_datasets", ["status"])
    op.create_index("ix_golden_datasets_tenant", "golden_datasets", ["tenant_id", "status"])

    # 2. 创建 golden_dataset_versions 表
    op.create_table(
        "golden_dataset_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("dataset_id", sa.String(64), sa.ForeignKey("golden_datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("applicable_config", postgresql.JSONB(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_golden_dataset_versions_dataset", "golden_dataset_versions", ["dataset_id", "version"], unique=True)

    # 3. 创建 eval_cases 表
    op.create_table(
        "eval_cases",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("dataset_id", sa.String(64), sa.ForeignKey("golden_datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("question", sa.Text(), nullable=False, comment="标准问题"),
        sa.Column("standard_answer", sa.Text(), nullable=False, comment="标准答案"),
        sa.Column("standard_document_id", sa.String(64), nullable=True),
        sa.Column("standard_chunk_id", sa.String(64), nullable=True),
        sa.Column("allowed_roles", postgresql.JSONB(), nullable=True, comment="允许角色"),
        sa.Column("forbidden_roles", postgresql.JSONB(), nullable=True, comment="禁止角色"),
        sa.Column("allowed_departments", postgresql.JSONB(), nullable=True, comment="允许部门"),
        sa.Column("should_refuse", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否应拒答"),
        sa.Column("question_type", sa.String(50), nullable=False, server_default="factual", comment="问题类型"),
        sa.Column("difficulty", sa.String(20), nullable=False, server_default="medium", comment="难度等级"),
        sa.Column("core_entities", postgresql.JSONB(), nullable=True, comment="核心实体"),
        sa.Column("time_conditions", sa.String(100), nullable=True, comment="时间条件"),
        sa.Column("location_conditions", sa.String(100), nullable=True, comment="地区条件"),
        sa.Column("tags", postgresql.JSONB(), nullable=True, comment="标签"),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0"), comment="权重"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="是否启用"),
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_eval_cases_dataset_active", "eval_cases", ["dataset_id", "is_active"])
    op.create_index("ix_eval_cases_type_difficulty", "eval_cases", ["question_type", "difficulty"])

    # 4. 创建 eval_runs 表
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("dataset_id", sa.String(64), sa.ForeignKey("golden_datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("dataset_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("access_context", postgresql.JSONB(), nullable=True),
        sa.Column("retrieval_config", postgresql.JSONB(), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("code_version", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_cases", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("passed_cases", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_cases", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_cases", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("skipped_cases", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metrics_summary", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_eval_runs_dataset_status", "eval_runs", ["dataset_id", "status"])
    op.create_index("ix_eval_runs_started", "eval_runs", ["started_at"])

    # 5. 创建 eval_results 表
    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("case_id", sa.String(64), sa.ForeignKey("eval_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        # 检索指标
        sa.Column("recall_at_k", sa.Float(), nullable=True),
        sa.Column("precision_at_k", sa.Float(), nullable=True),
        sa.Column("mrr", sa.Float(), nullable=True),
        sa.Column("ndcg", sa.Float(), nullable=True),
        sa.Column("standard_doc_hit", sa.Boolean(), nullable=True),
        sa.Column("standard_chunk_hit", sa.Boolean(), nullable=True),
        sa.Column("keyword_recall", sa.Float(), nullable=True),
        sa.Column("vector_recall", sa.Float(), nullable=True),
        sa.Column("hybrid_boost", sa.Float(), nullable=True),
        sa.Column("reranker_boost", sa.Float(), nullable=True),
        # 生成指标
        sa.Column("faithfulness", sa.Float(), nullable=True),
        sa.Column("answer_relevance", sa.Float(), nullable=True),
        sa.Column("context_relevance", sa.Float(), nullable=True),
        sa.Column("citation_accuracy", sa.Float(), nullable=True),
        sa.Column("citation_completeness", sa.Float(), nullable=True),
        sa.Column("no_answer_detection", sa.Boolean(), nullable=True),
        sa.Column("false_refusal", sa.Boolean(), nullable=True),
        sa.Column("hallucination_rate", sa.Float(), nullable=True),
        # 权限指标
        sa.Column("unauthorized_recall", sa.Boolean(), nullable=True),
        sa.Column("unauthorized_citation", sa.Boolean(), nullable=True),
        sa.Column("unauthorized_answer", sa.Boolean(), nullable=True),
        sa.Column("cross_permission_leak", sa.Boolean(), nullable=True),
        sa.Column("offline_doc_hit", sa.Boolean(), nullable=True),
        sa.Column("expired_doc_hit", sa.Boolean(), nullable=True),
        # 详细信息
        sa.Column("actual_output", sa.Text(), nullable=True),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_eval_results_run_case", "eval_results", ["run_id", "case_id"])
    op.create_index("ix_eval_results_status", "eval_results", ["run_id", "status"])


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("eval_cases")
    op.drop_table("golden_dataset_versions")
    op.drop_table("golden_datasets")