"""
标准问答服务（成员7）
提供标准问答的生命周期管理、状态机流转、审核发布等核心业务逻辑
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BusinessStateError,
    ResourceNotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.qa import (
    QA_STATUS_TRANSITIONS,
    CandidateQA,
    QAQualityCheck,
    QASource,
    QAReviewRecord,
    QuestionVariant,
    ReviewAction,
    StandardQA,
    QAStatus,
)

logger = get_logger(__name__)


class QAService:
    """标准问答服务"""

    # ========================================================================
    # 状态机
    # ========================================================================

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        """检查状态流转是否合法"""
        allowed = QA_STATUS_TRANSITIONS.get(current_status, [])
        return target_status in allowed

    @staticmethod
    def get_allowed_transitions(current_status: str) -> list[str]:
        """获取当前状态允许的目标状态列表"""
        return QA_STATUS_TRANSITIONS.get(current_status, [])

    @staticmethod
    def validate_transition(current_status: str, target_status: str) -> None:
        """验证状态流转，不合法时抛出异常"""
        if not QAService.can_transition(current_status, target_status):
            raise BusinessStateError(
                message=f"不允许从 {current_status} 转换到 {target_status}",
                current_state=current_status,
                expected_state=target_status,
            )

    # ========================================================================
    # 标准问答 CRUD
    # ========================================================================

    @staticmethod
    async def create_qa(
        db: AsyncSession,
        data: dict[str, Any],
        user_id: str,
        tenant_id: str,
    ) -> StandardQA:
        """创建标准问答（草稿状态）"""
        qa = StandardQA(
            question=data["question"],
            short_answer=data.get("short_answer"),
            detailed_answer=data.get("detailed_answer"),
            answer=data["answer"],
            keywords=data.get("keywords"),
            core_entities=data.get("core_entities"),
            category=data.get("category"),
            knowledge_base_id=data["knowledge_base_id"],
            applicable_roles=data.get("applicable_roles"),
            applicable_departments=data.get("applicable_departments"),
            access_scope=data.get("access_scope"),
            priority=data.get("priority", 0),
            effective_start=data.get("effective_start"),
            effective_end=data.get("effective_end"),
            status=QAStatus.DRAFT,
            version=1,
            is_machine_generated=False,
            metadata=data.get("metadata"),
            tenant_id=tenant_id,
            created_by=user_id,
        )
        db.add(qa)
        await db.flush()

        # 创建来源绑定
        for source_data in data.get("sources", []):
            source = QASource(
                qa_id=qa.id,
                document_id=source_data["document_id"],
                document_version=source_data["document_version"],
                chunk_id=source_data["chunk_id"],
                knowledge_base_id=source_data["knowledge_base_id"],
                is_primary=source_data.get("is_primary", False),
                relevance_score=source_data.get("relevance_score", 1.0),
                quote_text=source_data.get("quote_text"),
                tenant_id=tenant_id,
                created_by=user_id,
            )
            db.add(source)

        # 创建问题变体
        for variant_data in data.get("variants", []):
            variant = QuestionVariant(
                standard_qa_id=qa.id,
                variant_text=variant_data["variant_text"],
                variant_type=variant_data.get("variant_type", "manual"),
                tenant_id=tenant_id,
                created_by=user_id,
            )
            db.add(variant)

        await db.flush()
        logger.info("qa_created", qa_id=qa.id, question=qa.question[:50])
        return qa

    @staticmethod
    async def get_qa(
        db: AsyncSession,
        qa_id: str,
        load_relations: bool = False,
    ) -> StandardQA | None:
        """获取标准问答"""
        stmt = select(StandardQA).where(
            StandardQA.id == qa_id,
            StandardQA.deleted_at.is_(None),
        )
        if load_relations:
            stmt = stmt.options(
                selectinload(StandardQA.sources),
                selectinload(StandardQA.variants),
                selectinload(StandardQA.audit_records),
                selectinload(StandardQA.quality_checks),
            )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_qa_or_raise(
        db: AsyncSession,
        qa_id: str,
        load_relations: bool = False,
    ) -> StandardQA:
        """获取标准问答，不存在时抛出异常"""
        qa = await QAService.get_qa(db, qa_id, load_relations)
        if qa is None:
            raise ResourceNotFoundError("标准问答", qa_id)
        return qa

    @staticmethod
    async def update_qa(
        db: AsyncSession,
        qa_id: str,
        data: dict[str, Any],
        user_id: str,
    ) -> StandardQA:
        """更新标准问答"""
        qa = await QAService.get_qa_or_raise(db, qa_id)

        # 只允许在草稿或驳回状态修改
        if qa.status not in (QAStatus.DRAFT, QAStatus.REVIEW_REJECTED):
            raise BusinessStateError(
                message=f"当前状态 {qa.status} 不允许修改，请先驳回或返回修改",
                current_state=qa.status,
            )

        updatable_fields = [
            "question", "short_answer", "detailed_answer", "answer",
            "keywords", "core_entities", "category", "applicable_roles",
            "applicable_departments", "access_scope", "priority",
            "effective_start", "effective_end", "metadata",
        ]
        for field in updatable_fields:
            if field in data and data[field] is not None:
                setattr(qa, field, data[field])

        qa.updated_by = user_id
        await db.flush()
        logger.info("qa_updated", qa_id=qa_id)
        return qa

    @staticmethod
    async def list_qas(
        db: AsyncSession,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        category: str | None = None,
        knowledge_base_id: str | None = None,
        is_machine_generated: bool | None = None,
        reviewed_by: str | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> tuple[list[StandardQA], int]:
        """查询标准问答列表"""
        conditions = [
            StandardQA.tenant_id == tenant_id,
            StandardQA.deleted_at.is_(None),
        ]

        if keyword:
            conditions.append(
                or_(
                    StandardQA.question.ilike(f"%{keyword}%"),
                    StandardQA.answer.ilike(f"%{keyword}%"),
                )
            )
        if status:
            conditions.append(StandardQA.status == status)
        if category:
            conditions.append(StandardQA.category == category)
        if knowledge_base_id:
            conditions.append(StandardQA.knowledge_base_id == knowledge_base_id)
        if is_machine_generated is not None:
            conditions.append(StandardQA.is_machine_generated == is_machine_generated)
        if reviewed_by:
            conditions.append(StandardQA.reviewed_by == reviewed_by)

        # 总数
        count_stmt = select(func.count()).select_from(StandardQA).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar() or 0

        # 排序
        sort_col = getattr(StandardQA, sort_by, StandardQA.updated_at)
        if sort_order == "asc":
            order = sort_col.asc()
        else:
            order = sort_col.desc()

        # 分页
        stmt = (
            select(StandardQA)
            .where(and_(*conditions))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    # ========================================================================
    # 状态流转操作
    # ========================================================================

    @staticmethod
    async def submit_for_review(
        db: AsyncSession,
        qa_id: str,
        user_id: str,
    ) -> StandardQA:
        """提交审核"""
        qa = await QAService.get_qa_or_raise(db, qa_id)
        QAService.validate_transition(qa.status, QAStatus.PENDING_REVIEW)

        old_status = qa.status
        qa.status = QAStatus.PENDING_REVIEW
        qa.updated_by = user_id

        # 记录审核历史
        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.RETURN_FOR_MODIFICATION,
            status_from=old_status,
            status_to=QAStatus.PENDING_REVIEW,
            reviewer_id=user_id,
            review_time=datetime.now(timezone.utc),
            tenant_id=qa.tenant_id,
            created_by=user_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_submitted_for_review", qa_id=qa_id)
        return qa

    @staticmethod
    async def approve_review(
        db: AsyncSession,
        qa_id: str,
        reviewer_id: str,
        comment: str | None = None,
        review_details: dict | None = None,
    ) -> StandardQA:
        """审核通过 -> 待发布"""
        qa = await QAService.get_qa_or_raise(db, qa_id)
        QAService.validate_transition(qa.status, QAStatus.PENDING_PUBLISH)

        old_status = qa.status
        qa.status = QAStatus.PENDING_PUBLISH
        qa.reviewed_by = reviewer_id
        qa.reviewed_at = datetime.now(timezone.utc)
        qa.updated_by = reviewer_id

        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.APPROVE,
            status_from=old_status,
            status_to=QAStatus.PENDING_PUBLISH,
            comment=comment,
            reviewer_id=reviewer_id,
            review_time=datetime.now(timezone.utc),
            review_details=review_details,
            tenant_id=qa.tenant_id,
            created_by=reviewer_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_review_approved", qa_id=qa_id)
        return qa

    @staticmethod
    async def reject_review(
        db: AsyncSession,
        qa_id: str,
        reviewer_id: str,
        comment: str | None = None,
        review_details: dict | None = None,
    ) -> StandardQA:
        """审核驳回"""
        qa = await QAService.get_qa_or_raise(db, qa_id)
        QAService.validate_transition(qa.status, QAStatus.REVIEW_REJECTED)

        old_status = qa.status
        qa.status = QAStatus.REVIEW_REJECTED
        qa.updated_by = reviewer_id

        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.REJECT,
            status_from=old_status,
            status_to=QAStatus.REVIEW_REJECTED,
            comment=comment,
            reviewer_id=reviewer_id,
            review_time=datetime.now(timezone.utc),
            review_details=review_details,
            tenant_id=qa.tenant_id,
            created_by=reviewer_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_review_rejected", qa_id=qa_id)
        return qa

    @staticmethod
    async def return_for_modification(
        db: AsyncSession,
        qa_id: str,
        reviewer_id: str,
        comment: str | None = None,
    ) -> StandardQA:
        """返回修改"""
        qa = await QAService.get_qa_or_raise(db, qa_id)
        QAService.validate_transition(qa.status, QAStatus.DRAFT)

        old_status = qa.status
        qa.status = QAStatus.DRAFT
        qa.updated_by = reviewer_id

        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.RETURN_FOR_MODIFICATION,
            status_from=old_status,
            status_to=QAStatus.DRAFT,
            comment=comment,
            reviewer_id=reviewer_id,
            review_time=datetime.now(timezone.utc),
            tenant_id=qa.tenant_id,
            created_by=reviewer_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_returned_for_modification", qa_id=qa_id)
        return qa

    @staticmethod
    async def publish_qa(
        db: AsyncSession,
        qa_id: str,
        user_id: str,
        effective_start: datetime | None = None,
        effective_end: datetime | None = None,
    ) -> StandardQA:
        """发布标准问答"""
        qa = await QAService.get_qa_or_raise(db, qa_id, load_relations=True)

        # 发布前校验
        await QAService._validate_before_publish(qa)

        QAService.validate_transition(qa.status, QAStatus.PUBLISHED)

        old_status = qa.status
        qa.status = QAStatus.PUBLISHED
        qa.published_at = datetime.now(timezone.utc)
        if effective_start:
            qa.effective_start = effective_start
        if effective_end:
            qa.effective_end = effective_end
        qa.updated_by = user_id

        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.PUBLISH,
            status_from=old_status,
            status_to=QAStatus.PUBLISHED,
            reviewer_id=user_id,
            review_time=datetime.now(timezone.utc),
            tenant_id=qa.tenant_id,
            created_by=user_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_published", qa_id=qa_id)
        return qa

    @staticmethod
    async def disable_qa(
        db: AsyncSession,
        qa_id: str,
        user_id: str,
        reason: str,
    ) -> StandardQA:
        """停用标准问答"""
        qa = await QAService.get_qa_or_raise(db, qa_id)
        QAService.validate_transition(qa.status, QAStatus.DISABLED)

        old_status = qa.status
        qa.status = QAStatus.DISABLED
        qa.updated_by = user_id

        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.DISABLE,
            status_from=old_status,
            status_to=QAStatus.DISABLED,
            comment=reason,
            reviewer_id=user_id,
            review_time=datetime.now(timezone.utc),
            tenant_id=qa.tenant_id,
            created_by=user_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_disabled", qa_id=qa_id, reason=reason)
        return qa

    @staticmethod
    async def mark_as_expired(
        db: AsyncSession,
        qa_id: str,
        user_id: str,
    ) -> StandardQA:
        """标记为过期"""
        qa = await QAService.get_qa_or_raise(db, qa_id)
        QAService.validate_transition(qa.status, QAStatus.EXPIRED)

        old_status = qa.status
        qa.status = QAStatus.EXPIRED
        qa.expired_at = datetime.now(timezone.utc)
        qa.updated_by = user_id

        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.SUSPEND,
            status_from=old_status,
            status_to=QAStatus.EXPIRED,
            reviewer_id=user_id,
            review_time=datetime.now(timezone.utc),
            tenant_id=qa.tenant_id,
            created_by=user_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_expired", qa_id=qa_id)
        return qa

    @staticmethod
    async def mark_as_duplicate(
        db: AsyncSession,
        qa_id: str,
        duplicate_of_id: str,
        user_id: str,
    ) -> StandardQA:
        """标记为重复"""
        qa = await QAService.get_qa_or_raise(db, qa_id)
        # 验证目标问答存在
        target = await QAService.get_qa_or_raise(db, duplicate_of_id)

        old_status = qa.status
        qa.duplicate_of_id = duplicate_of_id
        qa.status = QAStatus.DISABLED
        qa.updated_by = user_id

        record = QAReviewRecord(
            qa_id=qa.id,
            action=ReviewAction.MARK_DUPLICATE,
            status_from=old_status,
            status_to=QAStatus.DISABLED,
            comment=f"标记为 {duplicate_of_id} 的重复问答",
            reviewer_id=user_id,
            review_time=datetime.now(timezone.utc),
            review_details={"duplicate_of_id": duplicate_of_id},
            tenant_id=qa.tenant_id,
            created_by=user_id,
        )
        db.add(record)
        await db.flush()
        logger.info("qa_marked_duplicate", qa_id=qa_id, duplicate_of=duplicate_of_id)
        return qa

    # ========================================================================
    # 发布前校验
    # ========================================================================

    @staticmethod
    async def _validate_before_publish(qa: StandardQA) -> None:
        """发布前校验"""
        errors: list[str] = []

        # 1. 来源有效性校验
        if not qa.sources:
            errors.append("至少需要一个来源绑定")

        # 2. 权限有效性校验
        if not qa.applicable_roles and not qa.applicable_departments:
            errors.append("建议至少设置适用角色或适用部门")

        # 3. 必要条件完整性校验
        if not qa.question or not qa.question.strip():
            errors.append("问题不能为空")
        if not qa.answer or not qa.answer.strip():
            errors.append("答案不能为空")

        # 4. 审核通过校验
        if qa.status not in (QAStatus.PENDING_PUBLISH, QAStatus.PUBLISHED):
            errors.append("必须先通过审核才能发布")

        # 5. 生效时间合理性校验
        if qa.effective_start and qa.effective_end:
            if qa.effective_start >= qa.effective_end:
                errors.append("生效开始时间必须早于结束时间")

        # 6. 未与现有问答冲突（简单检查）
        # 完整的冲突检测在质量检查中完成

        if errors:
            raise ValidationError(
                message="发布前校验失败",
                details={"errors": errors},
            )

    # ========================================================================
    # 文档版本联动
    # ========================================================================

    @staticmethod
    async def handle_document_version_change(
        db: AsyncSession,
        document_id: str,
        new_version: int,
        event_type: str,
        user_id: str = "system",
    ) -> list[StandardQA]:
        """处理文档版本变更，返回受影响的问答列表"""
        # 查找所有引用该文档的已发布或待复核问答
        stmt = (
            select(StandardQA)
            .join(QASource, QASource.qa_id == StandardQA.id)
            .where(
                QASource.document_id == document_id,
                StandardQA.status.in_([
                    QAStatus.PUBLISHED,
                    QAStatus.PENDING_REVIEW,
                    QAStatus.PENDING_PUBLISH,
                ]),
                StandardQA.deleted_at.is_(None),
            )
            .distinct()
        )
        result = await db.execute(stmt)
        affected_qas = list(result.scalars().all())

        for qa in affected_qas:
            old_status = qa.status
            reason = ""

            if event_type == "document.version.published":
                # 文档新版本发布，标记待复核
                qa.status = QAStatus.PENDING_REVIEW_AGAIN
                reason = f"来源文档 {document_id} 发布了新版本 v{new_version}"
            elif event_type == "document.paused":
                # 文档暂停，下线问答
                qa.status = QAStatus.DISABLED
                reason = f"来源文档 {document_id} 已暂停"
            elif event_type == "document.offlined":
                # 文档下线，下线问答
                qa.status = QAStatus.DISABLED
                reason = f"来源文档 {document_id} 已下线"
            elif event_type == "document.permission.changed":
                # 权限变更，标记待复核
                qa.status = QAStatus.PENDING_REVIEW_AGAIN
                reason = f"来源文档 {document_id} 的权限已变更"

            qa.updated_by = user_id

            # 更新来源版本
            await db.execute(
                update(QASource)
                .where(
                    QASource.qa_id == qa.id,
                    QASource.document_id == document_id,
                )
                .values(document_version=new_version)
            )

            # 记录审核日志
            record = QAReviewRecord(
                qa_id=qa.id,
                action=ReviewAction.MARK_SOURCE_ISSUE,
                status_from=old_status,
                status_to=qa.status,
                comment=reason,
                reviewer_id=user_id,
                review_time=datetime.now(timezone.utc),
                review_details={
                    "event_type": event_type,
                    "document_id": document_id,
                    "new_version": new_version,
                },
                tenant_id=qa.tenant_id,
                created_by=user_id,
            )
            db.add(record)

            logger.info(
                "qa_affected_by_document_change",
                qa_id=qa.id,
                event_type=event_type,
                old_status=old_status,
                new_status=qa.status,
            )

        await db.flush()
        return affected_qas

    # ========================================================================
    # 候选问答操作
    # ========================================================================

    @staticmethod
    async def create_candidate_from_generation(
        db: AsyncSession,
        candidate_data: dict[str, Any],
        tenant_id: str,
        user_id: str = "system",
    ) -> CandidateQA:
        """从生成结果创建候选问答"""
        candidate = CandidateQA(
            knowledge_base_id=candidate_data["knowledge_base_id"],
            question=candidate_data["question"],
            short_answer=candidate_data.get("short_answer"),
            detailed_answer=candidate_data.get("detailed_answer"),
            answer=candidate_data["answer"],
            variants=candidate_data.get("variants"),
            keywords=candidate_data.get("keywords"),
            core_entities=candidate_data.get("core_entities"),
            suggested_roles=candidate_data.get("suggested_roles"),
            suggested_departments=candidate_data.get("suggested_departments"),
            source_document_ids=candidate_data.get("source_document_ids"),
            source_chunk_ids=candidate_data.get("source_chunk_ids"),
            source=candidate_data.get("source", "ai_generate"),
            source_session_id=candidate_data.get("source_session_id"),
            generation_model=candidate_data.get("generation_model"),
            generation_prompt_version=candidate_data.get("generation_prompt_version"),
            confidence=candidate_data.get("confidence"),
            status="pending",
            metadata=candidate_data.get("metadata"),
            tenant_id=tenant_id,
            created_by=user_id,
        )
        db.add(candidate)
        await db.flush()
        return candidate

    @staticmethod
    async def list_candidates(
        db: AsyncSession,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        knowledge_base_id: str | None = None,
        source: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[CandidateQA], int]:
        """查询候选问答列表"""
        conditions = [
            CandidateQA.tenant_id == tenant_id,
            CandidateQA.deleted_at.is_(None),
        ]

        if keyword:
            conditions.append(
                or_(
                    CandidateQA.question.ilike(f"%{keyword}%"),
                    CandidateQA.answer.ilike(f"%{keyword}%"),
                )
            )
        if status:
            conditions.append(CandidateQA.status == status)
        if knowledge_base_id:
            conditions.append(CandidateQA.knowledge_base_id == knowledge_base_id)
        if source:
            conditions.append(CandidateQA.source == source)

        count_stmt = select(func.count()).select_from(CandidateQA).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar() or 0

        sort_col = getattr(CandidateQA, sort_by, CandidateQA.created_at)
        order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        stmt = (
            select(CandidateQA)
            .where(and_(*conditions))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    @staticmethod
    async def approve_candidate(
        db: AsyncSession,
        candidate_id: str,
        reviewer_id: str,
        comment: str | None = None,
    ) -> CandidateQA:
        """审核通过候选问答"""
        stmt = select(CandidateQA).where(
            CandidateQA.id == candidate_id,
            CandidateQA.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        candidate = result.scalar_one_or_none()
        if candidate is None:
            raise ResourceNotFoundError("候选问答", candidate_id)

        if candidate.status != "pending":
            raise BusinessStateError(
                message=f"候选问答状态为 {candidate.status}，无法审核",
                current_state=candidate.status,
            )

        candidate.status = "approved"
        candidate.reviewed_by = reviewer_id
        candidate.reviewed_at = datetime.now(timezone.utc)
        candidate.review_comment = comment
        await db.flush()
        logger.info("candidate_qa_approved", candidate_id=candidate_id)
        return candidate

    @staticmethod
    async def reject_candidate(
        db: AsyncSession,
        candidate_id: str,
        reviewer_id: str,
        comment: str | None = None,
    ) -> CandidateQA:
        """驳回候选问答"""
        stmt = select(CandidateQA).where(
            CandidateQA.id == candidate_id,
            CandidateQA.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        candidate = result.scalar_one_or_none()
        if candidate is None:
            raise ResourceNotFoundError("候选问答", candidate_id)

        candidate.status = "rejected"
        candidate.reviewed_by = reviewer_id
        candidate.reviewed_at = datetime.now(timezone.utc)
        candidate.review_comment = comment
        await db.flush()
        logger.info("candidate_qa_rejected", candidate_id=candidate_id)
        return candidate

    @staticmethod
    async def convert_candidate_to_standard(
        db: AsyncSession,
        candidate_id: str,
        user_id: str,
    ) -> StandardQA:
        """将候选问答转为标准问答"""
        stmt = select(CandidateQA).where(
            CandidateQA.id == candidate_id,
            CandidateQA.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        candidate = result.scalar_one_or_none()
        if candidate is None:
            raise ResourceNotFoundError("候选问答", candidate_id)

        if candidate.status != "approved":
            raise BusinessStateError(
                message="只有审核通过的候选问答才能转为标准问答",
                current_state=candidate.status,
            )

        qa_data = {
            "knowledge_base_id": candidate.knowledge_base_id,
            "question": candidate.question,
            "short_answer": candidate.short_answer,
            "detailed_answer": candidate.detailed_answer,
            "answer": candidate.answer,
            "keywords": candidate.keywords,
            "core_entities": candidate.core_entities,
            "applicable_roles": candidate.suggested_roles,
            "applicable_departments": candidate.suggested_departments,
            "is_machine_generated": True,
            "generation_model": candidate.generation_model,
            "generation_prompt_version": candidate.generation_prompt_version,
            "metadata": candidate.metadata,
            "sources": [],
            "variants": [],
        }

        # 构建来源
        if candidate.source_document_ids:
            for i, doc_id in enumerate(candidate.source_document_ids):
                chunk_id = (
                    candidate.source_chunk_ids[i]
                    if candidate.source_chunk_ids and i < len(candidate.source_chunk_ids)
                    else ""
                )
                qa_data["sources"].append({
                    "document_id": doc_id,
                    "document_version": 1,
                    "chunk_id": chunk_id,
                    "knowledge_base_id": candidate.knowledge_base_id,
                    "is_primary": i == 0,
                })

        # 构建变体
        if candidate.variants:
            for v_text in candidate.variants:
                qa_data["variants"].append({
                    "variant_text": v_text,
                    "variant_type": "auto_generated",
                })

        qa = await QAService.create_qa(db, qa_data, user_id, candidate.tenant_id)
        qa.status = QAStatus.AUTO_GENERATED
        qa.is_machine_generated = True

        # 关联候选到标准问答
        candidate.standard_qa_id = qa.id
        await db.flush()
        logger.info("candidate_converted_to_standard", candidate_id=candidate_id, qa_id=qa.id)
        return qa

    # ========================================================================
    # 审核记录
    # ========================================================================

    @staticmethod
    async def list_review_records(
        db: AsyncSession,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        qa_id: str | None = None,
        action: str | None = None,
        reviewer_id: str | None = None,
        sort_by: str = "review_time",
        sort_order: str = "desc",
    ) -> tuple[list[QAReviewRecord], int]:
        """查询审核记录"""
        conditions = [
            QAReviewRecord.tenant_id == tenant_id,
            QAReviewRecord.deleted_at.is_(None),
        ]
        if qa_id:
            conditions.append(QAReviewRecord.qa_id == qa_id)
        if action:
            conditions.append(QAReviewRecord.action == action)
        if reviewer_id:
            conditions.append(QAReviewRecord.reviewer_id == reviewer_id)

        count_stmt = select(func.count()).select_from(QAReviewRecord).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar() or 0

        sort_col = getattr(QAReviewRecord, sort_by, QAReviewRecord.review_time)
        order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        stmt = (
            select(QAReviewRecord)
            .where(and_(*conditions))
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total


# 单例
qa_service = QAService()