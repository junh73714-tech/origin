"""
评估模块模型（成员7）
包含 Golden Dataset、评估用例、评估运行、评估结果等模型
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class GoldenDataset(BaseModel):
    """
    Golden Dataset 模型
    评估标准数据集，包含多条评估用例
    """

    __tablename__ = "golden_datasets"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="数据集名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="数据集描述")
    version: Mapped[int] = mapped_column(default=1, nullable=False, comment="数据集版本号")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", comment="状态：draft / active / archived"
    )
    # 适用配置
    applicable_config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="适用配置（模型、参数等）"
    )
    change_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="版本变更说明"
    )
    case_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="用例数量")

    # 关系
    cases: Mapped[list["EvalCase"]] = relationship(
        "EvalCase", back_populates="dataset", cascade="all, delete-orphan"
    )
    versions: Mapped[list["GoldenDatasetVersion"]] = relationship(
        "GoldenDatasetVersion", back_populates="dataset", cascade="all, delete-orphan"
    )
    runs: Mapped[list["EvalRun"]] = relationship(
        "EvalRun", back_populates="dataset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_golden_datasets_status", "status"),
        Index("ix_golden_datasets_tenant", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<GoldenDataset {self.name} v{self.version}>"


class GoldenDatasetVersion(BaseModel):
    """
    Golden Dataset 版本模型
    记录数据集的版本历史
    """

    __tablename__ = "golden_dataset_versions"

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("golden_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属数据集",
    )
    version: Mapped[int] = mapped_column(nullable=False, comment="版本号")
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="变更说明")
    case_count: Mapped[int] = mapped_column(default=0, nullable=False, comment="该版本用例数量")
    applicable_config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="该版本适用配置"
    )
    snapshot: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="版本快照"
    )

    # 关系
    dataset: Mapped["GoldenDataset"] = relationship("GoldenDataset", back_populates="versions")

    __table_args__ = (
        Index("ix_golden_dataset_versions_dataset", "dataset_id", "version", unique=True),
    )

    def __repr__(self) -> str:
        return f"<GoldenDatasetVersion {self.dataset_id} v{self.version}>"


class EvalCase(BaseModel):
    """
    评估用例模型
    每条用例包含标准问题、标准答案、标准文档、标准 Chunk 等
    """

    __tablename__ = "eval_cases"

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("golden_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属数据集",
    )

    # === 标准内容 ===
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="标准问题")
    standard_answer: Mapped[str] = mapped_column(Text, nullable=False, comment="标准答案")
    standard_document_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="标准文档 ID"
    )
    standard_chunk_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="标准 Chunk ID"
    )

    # === 权限设定 ===
    allowed_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="允许角色")
    forbidden_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="禁止角色")
    allowed_departments: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="允许部门")

    # === 评估属性 ===
    should_refuse: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="是否应拒答"
    )
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="factual",
        comment="问题类型：factual / reasoning / comparison / calculation / policy",
    )
    difficulty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
        comment="难度等级：easy / medium / hard / expert",
    )
    core_entities: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="核心实体")
    time_conditions: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="时间条件")
    location_conditions: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="地区条件")

    # === 元数据 ===
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="标签")
    weight: Mapped[float] = mapped_column(default=1.0, nullable=False, comment="权重")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, comment="是否启用")

    # 关系
    dataset: Mapped["GoldenDataset"] = relationship("GoldenDataset", back_populates="cases")

    __table_args__ = (
        Index("ix_eval_cases_dataset_active", "dataset_id", "is_active"),
        Index("ix_eval_cases_type_difficulty", "question_type", "difficulty"),
    )

    def __repr__(self) -> str:
        return f"<EvalCase {self.id} [{self.question_type}] [{self.difficulty}]>"


class EvalRun(BaseModel):
    """
    评估运行模型
    记录每次评估任务的完整信息
    """

    __tablename__ = "eval_runs"

    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("golden_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="使用的数据集",
    )
    dataset_version: Mapped[int] = mapped_column(nullable=False, comment="数据集版本")

    # === 运行配置 ===
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending",
        comment="状态：pending / running / completed / failed / cancelled",
    )
    access_context: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="测试用的 AccessContext"
    )
    retrieval_config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="检索参数配置"
    )
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="模型版本")
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="提示词版本")
    code_version: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="代码版本")

    # === 运行时间 ===
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始时间"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    # === 运行结果汇总 ===
    total_cases: Mapped[int] = mapped_column(default=0, nullable=False, comment="总用例数")
    passed_cases: Mapped[int] = mapped_column(default=0, nullable=False, comment="通过用例数")
    failed_cases: Mapped[int] = mapped_column(default=0, nullable=False, comment="失败用例数")
    error_cases: Mapped[int] = mapped_column(default=0, nullable=False, comment="错误用例数")
    skipped_cases: Mapped[int] = mapped_column(default=0, nullable=False, comment="跳过用例数")

    # === 指标汇总 ===
    metrics_summary: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="指标汇总结果"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # 关系
    dataset: Mapped["GoldenDataset"] = relationship("GoldenDataset", back_populates="runs")
    results: Mapped[list["EvalResult"]] = relationship(
        "EvalResult", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_eval_runs_dataset_status", "dataset_id", "status"),
        Index("ix_eval_runs_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<EvalRun {self.id} [{self.status}]>"


class EvalResult(BaseModel):
    """
    评估结果模型
    记录每个用例的评估结果详情
    """

    __tablename__ = "eval_results"

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属评估运行",
    )
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("eval_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="评估用例",
    )

    # === 结果状态 ===
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending",
        comment="状态：pending / running / passed / failed / error / skipped",
    )

    # === 检索指标 ===
    recall_at_k: Mapped[float | None] = mapped_column(nullable=True, comment="Recall@K")
    precision_at_k: Mapped[float | None] = mapped_column(nullable=True, comment="Precision@K")
    mrr: Mapped[float | None] = mapped_column(nullable=True, comment="MRR")
    ndcg: Mapped[float | None] = mapped_column(nullable=True, comment="NDCG")
    standard_doc_hit: Mapped[bool | None] = mapped_column(nullable=True, comment="标准文档命中")
    standard_chunk_hit: Mapped[bool | None] = mapped_column(nullable=True, comment="标准 Chunk 命中")
    keyword_recall: Mapped[float | None] = mapped_column(nullable=True, comment="Keyword 召回率")
    vector_recall: Mapped[float | None] = mapped_column(nullable=True, comment="Vector 召回率")
    hybrid_boost: Mapped[float | None] = mapped_column(nullable=True, comment="混合检索提升率")
    reranker_boost: Mapped[float | None] = mapped_column(nullable=True, comment="Reranker 提升率")

    # === 生成指标 ===
    faithfulness: Mapped[float | None] = mapped_column(nullable=True, comment="Faithfulness")
    answer_relevance: Mapped[float | None] = mapped_column(nullable=True, comment="Answer Relevance")
    context_relevance: Mapped[float | None] = mapped_column(nullable=True, comment="Context Relevance")
    citation_accuracy: Mapped[float | None] = mapped_column(nullable=True, comment="引用准确率")
    citation_completeness: Mapped[float | None] = mapped_column(nullable=True, comment="引用完整率")
    no_answer_detection: Mapped[bool | None] = mapped_column(nullable=True, comment="无答案识别率")
    false_refusal: Mapped[bool | None] = mapped_column(nullable=True, comment="错误拒答")
    hallucination_rate: Mapped[float | None] = mapped_column(nullable=True, comment="幻觉率")

    # === 权限指标 ===
    unauthorized_recall: Mapped[bool | None] = mapped_column(nullable=True, comment="越权召回")
    unauthorized_citation: Mapped[bool | None] = mapped_column(nullable=True, comment="越权引用")
    unauthorized_answer: Mapped[bool | None] = mapped_column(nullable=True, comment="越权回答")
    cross_permission_leak: Mapped[bool | None] = mapped_column(nullable=True, comment="跨权限缓存泄露")
    offline_doc_hit: Mapped[bool | None] = mapped_column(nullable=True, comment="下线文档命中")
    expired_doc_hit: Mapped[bool | None] = mapped_column(nullable=True, comment="过期文档命中")

    # === 详细信息 ===
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实际输出")
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True, comment="期望输出")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    execution_time_ms: Mapped[float | None] = mapped_column(nullable=True, comment="执行耗时(ms)")
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="详细信息")

    # 关系
    run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="results")
    case: Mapped["EvalCase"] = relationship("EvalCase")

    __table_args__ = (
        Index("ix_eval_results_run_case", "run_id", "case_id"),
        Index("ix_eval_results_status", "run_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<EvalResult {self.run_id} case={self.case_id} [{self.status}]>"