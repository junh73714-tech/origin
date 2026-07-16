"""
评估服务（成员7）
提供 Golden Dataset 管理、评估运行、指标计算等核心业务逻辑
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.evaluation import (
    EvalCase,
    EvalResult,
    EvalRun,
    GoldenDataset,
    GoldenDatasetVersion,
)

logger = get_logger(__name__)


class EvaluationService:
    """评估服务"""

    # ========================================================================
    # Golden Dataset 管理
    # ========================================================================

    @staticmethod
    async def create_dataset(
        db: AsyncSession,
        data: dict[str, Any],
        user_id: str,
        tenant_id: str,
    ) -> GoldenDataset:
        """创建 Golden Dataset"""
        dataset = GoldenDataset(
            name=data["name"],
            description=data.get("description"),
            applicable_config=data.get("applicable_config"),
            change_summary=data.get("change_summary", "初始版本"),
            status="draft",
            version=1,
            case_count=0,
            tenant_id=tenant_id,
            created_by=user_id,
        )
        db.add(dataset)
        await db.flush()

        # 创建初始版本记录
        version_record = GoldenDatasetVersion(
            dataset_id=dataset.id,
            version=1,
            change_summary=data.get("change_summary", "初始版本"),
            case_count=0,
            applicable_config=data.get("applicable_config"),
            tenant_id=tenant_id,
            created_by=user_id,
        )
        db.add(version_record)
        await db.flush()

        logger.info("dataset_created", dataset_id=dataset.id, name=dataset.name)
        return dataset

    @staticmethod
    async def get_dataset(
        db: AsyncSession,
        dataset_id: str,
        load_relations: bool = False,
    ) -> GoldenDataset | None:
        """获取数据集"""
        stmt = select(GoldenDataset).where(
            GoldenDataset.id == dataset_id,
            GoldenDataset.deleted_at.is_(None),
        )
        if load_relations:
            stmt = stmt.options(
                selectinload(GoldenDataset.cases),
                selectinload(GoldenDataset.versions),
            )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_dataset_or_raise(
        db: AsyncSession,
        dataset_id: str,
    ) -> GoldenDataset:
        """获取数据集，不存在时抛出异常"""
        dataset = await EvaluationService.get_dataset(db, dataset_id)
        if dataset is None:
            raise ResourceNotFoundError("Golden Dataset", dataset_id)
        return dataset

    @staticmethod
    async def list_datasets(
        db: AsyncSession,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> tuple[list[GoldenDataset], int]:
        """查询数据集列表"""
        conditions = [
            GoldenDataset.tenant_id == tenant_id,
            GoldenDataset.deleted_at.is_(None),
        ]
        if keyword:
            conditions.append(GoldenDataset.name.ilike(f"%{keyword}%"))
        if status:
            conditions.append(GoldenDataset.status == status)

        count_stmt = select(func.count()).select_from(GoldenDataset).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar() or 0

        sort_col = getattr(GoldenDataset, sort_by, GoldenDataset.updated_at)
        order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        stmt = (
            select(GoldenDataset)
            .where(and_(*conditions))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    # ========================================================================
    # 评估用例管理
    # ========================================================================

    @staticmethod
    async def add_case(
        db: AsyncSession,
        dataset_id: str,
        data: dict[str, Any],
        user_id: str,
        tenant_id: str,
    ) -> EvalCase:
        """添加评估用例"""
        dataset = await EvaluationService.get_dataset_or_raise(db, dataset_id)

        case = EvalCase(
            dataset_id=dataset_id,
            question=data["question"],
            standard_answer=data["standard_answer"],
            standard_document_id=data.get("standard_document_id"),
            standard_chunk_id=data.get("standard_chunk_id"),
            allowed_roles=data.get("allowed_roles"),
            forbidden_roles=data.get("forbidden_roles"),
            allowed_departments=data.get("allowed_departments"),
            should_refuse=data.get("should_refuse", False),
            question_type=data.get("question_type", "factual"),
            difficulty=data.get("difficulty", "medium"),
            core_entities=data.get("core_entities"),
            time_conditions=data.get("time_conditions"),
            location_conditions=data.get("location_conditions"),
            tags=data.get("tags"),
            weight=data.get("weight", 1.0),
            tenant_id=tenant_id,
            created_by=user_id,
        )
        db.add(case)

        # 更新用例计数
        dataset.case_count = (dataset.case_count or 0) + 1
        await db.flush()
        return case

    @staticmethod
    async def batch_add_cases(
        db: AsyncSession,
        dataset_id: str,
        cases_data: list[dict[str, Any]],
        user_id: str,
        tenant_id: str,
    ) -> list[EvalCase]:
        """批量添加评估用例"""
        cases = []
        for data in cases_data:
            case = await EvaluationService.add_case(
                db, dataset_id, data, user_id, tenant_id
            )
            cases.append(case)
        return cases

    @staticmethod
    async def list_cases(
        db: AsyncSession,
        dataset_id: str,
        page: int = 1,
        page_size: int = 20,
        question_type: str | None = None,
        difficulty: str | None = None,
        is_active: bool | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[EvalCase], int]:
        """查询评估用例列表"""
        conditions = [
            EvalCase.dataset_id == dataset_id,
            EvalCase.deleted_at.is_(None),
        ]
        if question_type:
            conditions.append(EvalCase.question_type == question_type)
        if difficulty:
            conditions.append(EvalCase.difficulty == difficulty)
        if is_active is not None:
            conditions.append(EvalCase.is_active == is_active)

        count_stmt = select(func.count()).select_from(EvalCase).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar() or 0

        sort_col = getattr(EvalCase, sort_by, EvalCase.created_at)
        order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        stmt = (
            select(EvalCase)
            .where(and_(*conditions))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    # ========================================================================
    # 评估运行
    # ========================================================================

    @staticmethod
    async def create_run(
        db: AsyncSession,
        data: dict[str, Any],
        user_id: str,
        tenant_id: str,
    ) -> EvalRun:
        """创建评估运行"""
        dataset = await EvaluationService.get_dataset_or_raise(
            db, data["dataset_id"], load_relations=True
        )

        # 获取活跃用例
        active_cases = [c for c in dataset.cases if c.is_active]

        run = EvalRun(
            dataset_id=dataset.id,
            dataset_version=dataset.version,
            status="pending",
            access_context=data.get("access_context"),
            retrieval_config=data.get("retrieval_config"),
            model_version=data.get("model_version"),
            prompt_version=data.get("prompt_version"),
            code_version=data.get("code_version"),
            total_cases=len(active_cases),
            tenant_id=tenant_id,
            created_by=user_id,
        )
        db.add(run)
        await db.flush()

        # 为每个用例创建待评估结果记录
        for case in active_cases:
            result = EvalResult(
                run_id=run.id,
                case_id=case.id,
                status="pending",
                tenant_id=tenant_id,
                created_by=user_id,
            )
            db.add(result)

        await db.flush()
        logger.info("eval_run_created", run_id=run.id, total_cases=len(active_cases))
        return run

    @staticmethod
    async def get_run(
        db: AsyncSession,
        run_id: str,
    ) -> EvalRun | None:
        """获取评估运行"""
        stmt = (
            select(EvalRun)
            .where(EvalRun.id == run_id)
            .options(selectinload(EvalRun.results))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_runs(
        db: AsyncSession,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        dataset_id: str | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[EvalRun], int]:
        """查询评估运行列表"""
        conditions = [
            EvalRun.tenant_id == tenant_id,
            EvalRun.deleted_at.is_(None),
        ]
        if dataset_id:
            conditions.append(EvalRun.dataset_id == dataset_id)
        if status:
            conditions.append(EvalRun.status == status)

        count_stmt = select(func.count()).select_from(EvalRun).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar() or 0

        sort_col = getattr(EvalRun, sort_by, EvalRun.created_at)
        order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        stmt = (
            select(EvalRun)
            .where(and_(*conditions))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def update_run_metrics(
        db: AsyncSession,
        run_id: str,
    ) -> EvalRun:
        """更新评估运行的指标汇总"""
        run = await EvaluationService.get_run(db, run_id)
        if run is None:
            raise ResourceNotFoundError("评估运行", run_id)

        # 汇总所有结果
        results = run.results or []
        completed = [r for r in results if r.status in ("passed", "failed")]

        if not completed:
            return run

        # 计算汇总指标
        metrics = {
            "retrieval": {
                "avg_recall_at_k": sum(
                    r.recall_at_k for r in completed if r.recall_at_k is not None
                ) / max(len([r for r in completed if r.recall_at_k is not None]), 1),
                "avg_precision_at_k": sum(
                    r.precision_at_k for r in completed if r.precision_at_k is not None
                ) / max(len([r for r in completed if r.precision_at_k is not None]), 1),
                "avg_mrr": sum(
                    r.mrr for r in completed if r.mrr is not None
                ) / max(len([r for r in completed if r.mrr is not None]), 1),
                "standard_doc_hit_rate": sum(
                    1 for r in completed if r.standard_doc_hit
                ) / max(len(completed), 1),
                "standard_chunk_hit_rate": sum(
                    1 for r in completed if r.standard_chunk_hit
                ) / max(len(completed), 1),
            },
            "generation": {
                "avg_faithfulness": sum(
                    r.faithfulness for r in completed if r.faithfulness is not None
                ) / max(len([r for r in completed if r.faithfulness is not None]), 1),
                "avg_answer_relevance": sum(
                    r.answer_relevance for r in completed if r.answer_relevance is not None
                ) / max(len([r for r in completed if r.answer_relevance is not None]), 1),
                "avg_context_relevance": sum(
                    r.context_relevance for r in completed if r.context_relevance is not None
                ) / max(len([r for r in completed if r.context_relevance is not None]), 1),
                "hallucination_rate": sum(
                    r.hallucination_rate for r in completed if r.hallucination_rate is not None
                ) / max(len([r for r in completed if r.hallucination_rate is not None]), 1),
            },
            "permission": {
                "unauthorized_recall_count": sum(
                    1 for r in completed if r.unauthorized_recall
                ),
                "unauthorized_citation_count": sum(
                    1 for r in completed if r.unauthorized_citation
                ),
                "unauthorized_answer_count": sum(
                    1 for r in completed if r.unauthorized_answer
                ),
                "cross_permission_leak_count": sum(
                    1 for r in completed if r.cross_permission_leak
                ),
            },
        }

        run.metrics_summary = metrics
        run.passed_cases = sum(1 for r in completed if r.status == "passed")
        run.failed_cases = sum(1 for r in completed if r.status == "failed")
        run.error_cases = sum(1 for r in results if r.status == "error")
        run.skipped_cases = sum(1 for r in results if r.status == "skipped")

        await db.flush()
        return run


# 单例
evaluation_service = EvaluationService()