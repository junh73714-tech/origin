"""
评估模块单元测试（成员7）
测试 Golden Dataset、评估用例、评估运行、指标计算等核心逻辑
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.evaluation import (
    GoldenDataset,
    GoldenDatasetVersion,
    EvalCase,
    EvalRun,
    EvalResult,
)


class TestGoldenDataset:
    """Golden Dataset 测试"""

    def test_dataset_creation(self):
        """测试数据集创建"""
        dataset = GoldenDataset(
            name="测试数据集",
            description="用于测试标准问答匹配效果",
            version=1,
            status="draft",
            tenant_id="t1",
            created_by="u1",
        )
        assert dataset.name == "测试数据集"
        assert dataset.version == 1
        assert dataset.status == "draft"
        assert dataset.case_count == 0

    def test_dataset_version_creation(self):
        """测试数据集版本创建"""
        version = GoldenDatasetVersion(
            dataset_id="ds1",
            version=1,
            change_summary="初始版本",
            case_count=10,
            tenant_id="t1",
            created_by="u1",
        )
        assert version.dataset_id == "ds1"
        assert version.version == 1
        assert version.case_count == 10


class TestEvalCase:
    """评估用例测试"""

    def test_eval_case_factual(self):
        """测试事实类评估用例"""
        case = EvalCase(
            dataset_id="ds1",
            question="公司年假政策是什么？",
            standard_answer="正式员工每年享有15天年假。",
            should_refuse=False,
            question_type="factual",
            difficulty="easy",
            core_entities=["年假", "15天"],
            tenant_id="t1",
            created_by="u1",
        )
        assert case.should_refuse is False
        assert case.question_type == "factual"
        assert case.difficulty == "easy"
        assert case.is_active is True

    def test_eval_case_should_refuse(self):
        """测试应拒答用例"""
        case = EvalCase(
            dataset_id="ds1",
            question="未公开的机密信息是什么？",
            standard_answer="",
            should_refuse=True,
            question_type="factual",
            difficulty="hard",
            tenant_id="t1",
            created_by="u1",
        )
        assert case.should_refuse is True
        assert case.difficulty == "hard"

    def test_eval_case_with_permissions(self):
        """测试含权限设定的用例"""
        case = EvalCase(
            dataset_id="ds1",
            question="部门预算信息",
            standard_answer="部门预算为 XXX 元",
            allowed_roles=["manager", "finance"],
            forbidden_roles=["intern"],
            question_type="factual",
            tenant_id="t1",
            created_by="u1",
        )
        assert "manager" in (case.allowed_roles or [])
        assert "intern" in (case.forbidden_roles or [])

    def test_eval_case_weight(self):
        """测试用例权重"""
        case = EvalCase(
            dataset_id="ds1",
            question="测试",
            standard_answer="答案",
            question_type="factual",
            weight=2.0,
            tenant_id="t1",
            created_by="u1",
        )
        assert case.weight == 2.0


class TestEvalRun:
    """评估运行测试"""

    def test_eval_run_creation(self):
        """测试评估运行创建"""
        run = EvalRun(
            dataset_id="ds1",
            dataset_version=1,
            status="pending",
            total_cases=10,
            tenant_id="t1",
            created_by="u1",
        )
        assert run.status == "pending"
        assert run.total_cases == 10
        assert run.passed_cases == 0
        assert run.failed_cases == 0

    def test_eval_run_with_config(self):
        """测试携带配置的评估运行"""
        run = EvalRun(
            dataset_id="ds1",
            dataset_version=1,
            status="pending",
            retrieval_config={"top_k": 10, "rerank": True},
            model_version="gpt-4o",
            prompt_version="1.0.0",
            code_version="abc123",
            total_cases=10,
            tenant_id="t1",
            created_by="u1",
        )
        assert run.retrieval_config is not None
        assert run.retrieval_config["top_k"] == 10
        assert run.model_version == "gpt-4o"
        assert run.code_version == "abc123"


class TestEvalResult:
    """评估结果测试"""

    def test_eval_result_retrieval_metrics(self):
        """测试检索指标"""
        result = EvalResult(
            run_id="run1",
            case_id="case1",
            status="passed",
            recall_at_k=0.85,
            precision_at_k=0.78,
            mrr=0.72,
            ndcg=0.80,
            standard_doc_hit=True,
            standard_chunk_hit=True,
            keyword_recall=0.70,
            vector_recall=0.82,
            hybrid_boost=0.05,
            reranker_boost=0.08,
            tenant_id="t1",
            created_by="u1",
        )
        assert result.recall_at_k == 0.85
        assert result.standard_doc_hit is True
        assert result.hybrid_boost == 0.05

    def test_eval_result_generation_metrics(self):
        """测试生成指标"""
        result = EvalResult(
            run_id="run1",
            case_id="case1",
            status="passed",
            faithfulness=0.90,
            answer_relevance=0.88,
            context_relevance=0.85,
            citation_accuracy=0.92,
            citation_completeness=0.87,
            hallucination_rate=0.05,
            tenant_id="t1",
            created_by="u1",
        )
        assert result.faithfulness == 0.90
        assert result.citation_accuracy == 0.92
        assert result.hallucination_rate == 0.05

    def test_eval_result_permission_metrics(self):
        """测试权限指标"""
        result = EvalResult(
            run_id="run1",
            case_id="case1",
            status="passed",
            unauthorized_recall=False,
            unauthorized_citation=False,
            unauthorized_answer=False,
            cross_permission_leak=False,
            offline_doc_hit=False,
            expired_doc_hit=False,
            tenant_id="t1",
            created_by="u1",
        )
        # 验收目标：所有越权指标为 0
        assert result.unauthorized_recall is False
        assert result.unauthorized_citation is False
        assert result.unauthorized_answer is False
        assert result.cross_permission_leak is False
        assert result.offline_doc_hit is False
        assert result.expired_doc_hit is False

    def test_eval_result_error(self):
        """测试错误结果"""
        result = EvalResult(
            run_id="run1",
            case_id="case1",
            status="error",
            error_message="LLM 调用超时",
            tenant_id="t1",
            created_by="u1",
        )
        assert result.status == "error"
        assert result.error_message == "LLM 调用超时"


class TestEvaluationService:
    """评估服务测试"""

    @pytest.mark.asyncio
    async def test_create_dataset(self):
        """测试创建数据集"""
        from app.services.evaluation_service import evaluation_service

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        dataset = await evaluation_service.create_dataset(
            db=mock_db,
            data={
                "name": "测试数据集",
                "description": "测试描述",
                "change_summary": "初始版本",
            },
            user_id="u1",
            tenant_id="t1",
        )
        assert dataset.name == "测试数据集"
        assert dataset.version == 1
        assert dataset.status == "draft"

    @pytest.mark.asyncio
    async def test_add_case(self):
        """测试添加评估用例"""
        from app.services.evaluation_service import evaluation_service

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock the dataset retrieval
        dataset = GoldenDataset(
            name="测试数据集",
            version=1,
            status="draft",
            tenant_id="t1",
            created_by="u1",
        )
        evaluation_service.get_dataset_or_raise = AsyncMock(return_value=dataset)

        case = await evaluation_service.add_case(
            db=mock_db,
            dataset_id="ds1",
            data={
                "question": "公司年假政策？",
                "standard_answer": "15天年假",
                "question_type": "factual",
                "difficulty": "easy",
                "should_refuse": False,
            },
            user_id="u1",
            tenant_id="t1",
        )
        assert case.question == "公司年假政策？"
        assert case.question_type == "factual"
        assert case.difficulty == "easy"

    @pytest.mark.asyncio
    async def test_create_run(self):
        """测试创建评估运行"""
        from app.services.evaluation_service import evaluation_service

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock dataset with cases
        case1 = EvalCase(
            dataset_id="ds1",
            question="问题1",
            standard_answer="答案1",
            question_type="factual",
            is_active=True,
            tenant_id="t1",
            created_by="u1",
        )
        case2 = EvalCase(
            dataset_id="ds1",
            question="问题2",
            standard_answer="答案2",
            question_type="factual",
            is_active=True,
            tenant_id="t1",
            created_by="u1",
        )
        dataset = GoldenDataset(
            name="测试数据集",
            version=1,
            status="active",
            case_count=2,
            tenant_id="t1",
            created_by="u1",
        )
        dataset.cases = [case1, case2]

        evaluation_service.get_dataset_or_raise = AsyncMock(return_value=dataset)

        run = await evaluation_service.create_run(
            db=mock_db,
            data={
                "dataset_id": "ds1",
                "model_version": "gpt-4o",
                "prompt_version": "1.0.0",
            },
            user_id="u1",
            tenant_id="t1",
        )
        assert run.status == "pending"
        assert run.total_cases == 2
        assert run.dataset_version == 1

    @pytest.mark.asyncio
    async def test_update_run_metrics(self):
        """测试更新运行指标汇总"""
        from app.services.evaluation_service import evaluation_service

        mock_db = AsyncMock()

        # Create results with known metrics
        results = [
            EvalResult(
                run_id="run1",
                case_id="case1",
                status="passed",
                recall_at_k=0.9,
                precision_at_k=0.8,
                mrr=0.85,
                faithfulness=0.95,
                answer_relevance=0.9,
                unauthorized_recall=False,
                unauthorized_citation=False,
                tenant_id="t1",
                created_by="u1",
            ),
            EvalResult(
                run_id="run1",
                case_id="case2",
                status="passed",
                recall_at_k=0.8,
                precision_at_k=0.7,
                mrr=0.75,
                faithfulness=0.85,
                answer_relevance=0.8,
                unauthorized_recall=False,
                unauthorized_citation=True,
                tenant_id="t1",
                created_by="u1",
            ),
        ]

        run = EvalRun(
            dataset_id="ds1",
            dataset_version=1,
            status="completed",
            total_cases=2,
            tenant_id="t1",
            created_by="u1",
        )
        run.results = results

        evaluation_service.get_run = AsyncMock(return_value=run)

        updated_run = await evaluation_service.update_run_metrics(mock_db, "run1")
        assert updated_run.metrics_summary is not None
        metrics = updated_run.metrics_summary
        assert metrics["retrieval"]["avg_recall_at_k"] == 0.85
        assert metrics["retrieval"]["avg_precision_at_k"] == 0.75
        assert metrics["generation"]["avg_faithfulness"] == 0.90
        assert metrics["permission"]["unauthorized_citation_count"] == 1


class TestEvalCaseTypes:
    """评估用例类型测试"""

    def test_all_question_types(self):
        """测试所有问题类型"""
        types = ["factual", "reasoning", "comparison", "calculation", "policy"]
        for t in types:
            case = EvalCase(
                dataset_id="ds1",
                question="测试",
                standard_answer="测试",
                question_type=t,
                tenant_id="t1",
                created_by="u1",
            )
            assert case.question_type == t

    def test_all_difficulties(self):
        """测试所有难度等级"""
        difficulties = ["easy", "medium", "hard", "expert"]
        for d in difficulties:
            case = EvalCase(
                dataset_id="ds1",
                question="测试",
                standard_answer="测试",
                question_type="factual",
                difficulty=d,
                tenant_id="t1",
                created_by="u1",
            )
            assert case.difficulty == d


class TestEvalSchema:
    """评估 Schema 测试"""

    def test_eval_case_create(self):
        """测试创建评估用例 Schema"""
        from app.schemas.evaluation import EvalCaseCreate

        data = EvalCaseCreate(
            question="公司年假政策？",
            standard_answer="15天年假",
            question_type="factual",
            difficulty="easy",
            core_entities=["年假"],
            tags=["HR", "福利"],
        )
        assert data.question == "公司年假政策？"
        assert data.core_entities == ["年假"]
        assert data.tags == ["HR", "福利"]

    def test_eval_run_create(self):
        """测试创建评估运行 Schema"""
        from app.schemas.evaluation import EvalRunCreate

        data = EvalRunCreate(
            dataset_id="ds1",
            model_version="gpt-4o",
            prompt_version="1.0.0",
            retrieval_config={"top_k": 10},
        )
        assert data.dataset_id == "ds1"
        assert data.model_version == "gpt-4o"
        assert data.retrieval_config["top_k"] == 10

    def test_golden_dataset_create(self):
        """测试创建 Golden Dataset Schema"""
        from app.schemas.evaluation import GoldenDatasetCreate

        data = GoldenDatasetCreate(
            name="测试数据集",
            description="测试描述",
            change_summary="初始版本",
        )
        assert data.name == "测试数据集"
        assert data.status is None  # 默认值

    def test_question_type_enum(self):
        """测试问题类型枚举值"""
        from app.schemas.evaluation import EvalCaseCreate

        data = EvalCaseCreate(
            question="比较A和B的区别？",
            standard_answer="A和B的区别是...",
            question_type="comparison",
            difficulty="medium",
            should_refuse=False,
        )
        assert data.question_type == "comparison"
        assert data.difficulty == "medium"