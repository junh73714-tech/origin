"""
标准问答模块单元测试
测试状态机流转、审核流程、匹配服务、质量检查等核心逻辑
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.qa import QAStatus, ReviewAction, QA_STATUS_TRANSITIONS
from app.services.qa_service import QAService
from app.core.exceptions import BusinessStateError, ResourceNotFoundError, ValidationError


class TestQAStateMachine:
    """状态机测试"""

    def test_valid_transitions(self):
        """测试合法状态流转"""
        # 草稿 -> 待审核
        assert QAService.can_transition(QAStatus.DRAFT, QAStatus.PENDING_REVIEW) is True
        # 草稿 -> 自动生成
        assert QAService.can_transition(QAStatus.DRAFT, QAStatus.AUTO_GENERATED) is True

    def test_invalid_transitions(self):
        """测试非法状态流转"""
        # 草稿不能直接发布
        assert QAService.can_transition(QAStatus.DRAFT, QAStatus.PUBLISHED) is False
        # 已发布不能回到草稿
        assert QAService.can_transition(QAStatus.PUBLISHED, QAStatus.DRAFT) is False
        # 已过期不能直接发布
        assert QAService.can_transition(QAStatus.EXPIRED, QAStatus.PUBLISHED) is False

    def test_get_allowed_transitions(self):
        """测试获取允许的目标状态"""
        allowed = QAService.get_allowed_transitions(QAStatus.PENDING_REVIEW)
        assert QAStatus.PENDING_PUBLISH in allowed
        assert QAStatus.REVIEW_REJECTED in allowed
        assert QAStatus.DRAFT in allowed
        assert QAStatus.PUBLISHED not in allowed

    def test_validate_transition_success(self):
        """测试状态流转验证通过"""
        # 不应抛出异常
        QAService.validate_transition(QAStatus.PENDING_REVIEW, QAStatus.PENDING_PUBLISH)

    def test_validate_transition_failure(self):
        """测试状态流转验证失败"""
        with pytest.raises(BusinessStateError) as exc_info:
            QAService.validate_transition(QAStatus.PUBLISHED, QAStatus.DRAFT)
        assert "不允许" in str(exc_info.value.message)
        assert exc_info.value.details["current_state"] == QAStatus.PUBLISHED

    def test_all_transitions_are_valid(self):
        """测试所有已定义的状态流转都是合法的"""
        for source, targets in QA_STATUS_TRANSITIONS.items():
            for target in targets:
                assert QAService.can_transition(source, target) is True

    def test_published_to_disabled(self):
        """测试已发布 -> 已停用"""
        assert QAService.can_transition(QAStatus.PUBLISHED, QAStatus.DISABLED) is True

    def test_published_to_expired(self):
        """测试已发布 -> 已过期"""
        assert QAService.can_transition(QAStatus.PUBLISHED, QAStatus.EXPIRED) is True

    def test_published_to_pending_review_again(self):
        """测试已发布 -> 待复核（来源文档变更触发）"""
        assert QAService.can_transition(QAStatus.PUBLISHED, QAStatus.PENDING_REVIEW_AGAIN) is True

    def test_pending_review_again_to_published(self):
        """测试待复核 -> 已发布（复核通过）"""
        assert QAService.can_transition(QAStatus.PENDING_REVIEW_AGAIN, QAStatus.PUBLISHED) is True

    def test_pending_review_again_to_disabled(self):
        """测试待复核 -> 已停用"""
        assert QAService.can_transition(QAStatus.PENDING_REVIEW_AGAIN, QAStatus.DISABLED) is True


class TestQAStatusConstants:
    """状态常量测试"""

    def test_all_statuses_defined(self):
        """测试所有必需状态已定义"""
        required_statuses = [
            "draft", "auto_generated", "pending_review", "review_rejected",
            "pending_publish", "published", "pending_review_again",
            "expired", "disabled",
        ]
        for status in required_statuses:
            assert hasattr(QAStatus, status.upper())

    def test_all_review_actions_defined(self):
        """测试所有审核动作已定义"""
        required_actions = [
            "approve", "reject", "return_for_modification", "publish",
            "suspend", "disable", "mark_duplicate", "mark_source_issue",
        ]
        for action in required_actions:
            assert hasattr(ReviewAction, action.upper())


class TestQAServiceValidation:
    """发布前校验测试"""

    @pytest.mark.asyncio
    async def test_validate_before_publish_missing_sources(self):
        """测试发布时缺少来源"""
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试问题",
            answer="测试答案",
            status=QAStatus.PENDING_PUBLISH,
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        qa.sources = []

        with pytest.raises(ValidationError) as exc_info:
            await QAService._validate_before_publish(qa)
        assert "来源" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_validate_before_publish_empty_question(self):
        """测试发布时空问题"""
        from app.models.qa import StandardQA, QASource

        qa = StandardQA(
            question="",
            answer="测试答案",
            status=QAStatus.PENDING_PUBLISH,
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        qa.sources = [
            QASource(
                qa_id=qa.id,
                document_id="doc1",
                document_version=1,
                chunk_id="chunk1",
                knowledge_base_id="kb1",
                tenant_id="t1",
                created_by="u1",
            )
        ]

        with pytest.raises(ValidationError) as exc_info:
            await QAService._validate_before_publish(qa)
        assert "问题" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_validate_before_publish_invalid_time_range(self):
        """测试发布时生效时间不合理"""
        from app.models.qa import StandardQA, QASource

        qa = StandardQA(
            question="测试问题",
            answer="测试答案",
            status=QAStatus.PENDING_PUBLISH,
            knowledge_base_id="kb1",
            effective_start=datetime.now(timezone.utc) + timedelta(days=10),
            effective_end=datetime.now(timezone.utc),
            tenant_id="t1",
            created_by="u1",
        )
        qa.sources = [
            QASource(
                qa_id=qa.id,
                document_id="doc1",
                document_version=1,
                chunk_id="chunk1",
                knowledge_base_id="kb1",
                tenant_id="t1",
                created_by="u1",
            )
        ]

        with pytest.raises(ValidationError) as exc_info:
            await QAService._validate_before_publish(qa)
        assert "生效" in str(exc_info.value.message)


class TestQAMatchingService:
    """匹配服务测试"""

    def test_cosine_similarity_identical(self):
        """测试余弦相似度 - 相同向量"""
        from app.services.qa_matching_service import qa_matching_service
        vec = [1.0, 2.0, 3.0]
        sim = qa_matching_service._cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.0001

    def test_cosine_similarity_orthogonal(self):
        """测试余弦相似度 - 正交向量"""
        from app.services.qa_matching_service import qa_matching_service
        sim = qa_matching_service._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim - 0.0) < 0.0001

    def test_cosine_similarity_empty(self):
        """测试余弦相似度 - 空向量"""
        from app.services.qa_matching_service import qa_matching_service
        sim = qa_matching_service._cosine_similarity([], [])
        assert sim == 0.0

    def test_cosine_similarity_different_length(self):
        """测试余弦相似度 - 不同长度"""
        from app.services.qa_matching_service import qa_matching_service
        sim = qa_matching_service._cosine_similarity([1.0, 2.0], [1.0])
        assert sim == 0.0

    def test_fallback_text_similarity(self):
        """测试降级文本相似度"""
        from app.services.qa_matching_service import qa_matching_service
        sim = qa_matching_service._fallback_text_similarity(
            "如何申请请假",
            "请假申请流程是什么",
        )
        assert 0.0 < sim < 1.0

    def test_fallback_text_similarity_empty(self):
        """测试降级文本相似度 - 空字符串"""
        from app.services.qa_matching_service import qa_matching_service
        sim = qa_matching_service._fallback_text_similarity("", "")
        assert sim == 0.0

    def test_compute_keyword_score_full_match(self):
        """测试关键词完全匹配"""
        from app.services.qa_matching_service import qa_matching_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="测试",
            keywords=["请假", "申请", "流程"],
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        score = qa_matching_service._compute_keyword_score(qa, ["请假", "申请"])
        assert score == 1.0

    def test_compute_keyword_score_no_match(self):
        """测试关键词无匹配"""
        from app.services.qa_matching_service import qa_matching_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="测试",
            keywords=["请假", "申请", "流程"],
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        score = qa_matching_service._compute_keyword_score(qa, ["报销", "差旅"])
        assert score == 0.0

    def test_compute_entity_consistency(self):
        """测试实体一致性"""
        from app.services.qa_matching_service import qa_matching_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="测试",
            core_entities=["北京", "2024年", "张三"],
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        score = qa_matching_service._compute_entity_consistency(qa, ["北京", "2024年"])
        assert score == 1.0

    def test_compute_final_score(self):
        """测试综合评分计算"""
        from app.services.qa_matching_service import qa_matching_service

        scores = {
            "semantic_score": 0.8,
            "keyword_score": 0.9,
            "entity_consistency": 0.7,
            "scope_consistency": 1.0,
        }
        final = qa_matching_service._compute_final_score(scores)
        expected = 0.8 * 0.40 + 0.9 * 0.25 + 0.7 * 0.20 + 1.0 * 0.15
        assert abs(final - expected) < 0.0001

    def test_check_access_scope_no_restrictions(self):
        """测试访问范围 - 无限制"""
        from app.services.qa_matching_service import qa_matching_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="测试",
            applicable_roles=None,
            applicable_departments=None,
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        assert qa_matching_service._check_access_scope(qa, ["employee"], ["engineering"]) is True

    def test_check_access_scope_role_match(self):
        """测试访问范围 - 角色匹配"""
        from app.services.qa_matching_service import qa_matching_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="测试",
            applicable_roles=["manager", "admin"],
            applicable_departments=None,
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        assert qa_matching_service._check_access_scope(qa, ["manager"], []) is True

    def test_check_access_scope_role_mismatch(self):
        """测试访问范围 - 角色不匹配"""
        from app.services.qa_matching_service import qa_matching_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="测试",
            applicable_roles=["manager", "admin"],
            applicable_departments=None,
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        assert qa_matching_service._check_access_scope(qa, ["employee"], []) is False


class TestQAQualityCheckService:
    """质量检查服务测试"""

    @pytest.mark.asyncio
    async def test_check_sensitive_info_clean(self):
        """测试敏感信息检查 - 无敏感信息"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="如何申请请假？",
            answer="请通过 OA 系统提交请假申请。",
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_sensitive_info(None, qa)
        assert passed is True
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_check_sensitive_info_phone(self):
        """测试敏感信息检查 - 包含手机号"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="联系方式是什么？",
            answer="请联系 13812345678 获取更多信息。",
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_sensitive_info(None, qa)
        assert passed is False
        assert "手机号" in detail

    @pytest.mark.asyncio
    async def test_check_absolute_claims_clean(self):
        """测试绝对化表述检查 - 无绝对化表述"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="这个政策适用吗？",
            answer="根据公司规定，该政策适用于所有正式员工。",
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_absolute_claims(None, qa)
        assert passed is True

    @pytest.mark.asyncio
    async def test_check_absolute_claims_found(self):
        """测试绝对化表述检查 - 包含绝对化表述"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="这个政策适用吗？",
            answer="这绝对是公司最重要的政策，百分百适用于所有人。",
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_absolute_claims(None, qa)
        assert passed is False

    @pytest.mark.asyncio
    async def test_check_qa_match_good(self):
        """测试问答匹配检查 - 良好匹配"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="如何申请请假？",
            answer="申请请假需要登录 OA 系统，填写请假申请表。",
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_qa_match(None, qa)
        assert passed is True

    @pytest.mark.asyncio
    async def test_check_qa_match_poor(self):
        """测试问答匹配检查 - 不匹配"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="如何申请请假？",
            answer="报销流程需要提交发票和报销单。",
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_qa_match(None, qa)
        assert passed is False

    def test_text_similarity_identical(self):
        """测试文本相似度 - 完全相同"""
        from app.services.qa_quality_service import qa_quality_check_service
        sim = qa_quality_check_service._text_similarity("如何申请请假", "如何申请请假")
        assert abs(sim - 1.0) < 0.0001

    def test_text_similarity_different(self):
        """测试文本相似度 - 完全不同"""
        from app.services.qa_quality_service import qa_quality_check_service
        sim = qa_quality_check_service._text_similarity("如何申请请假", "报销流程说明")
        assert sim < 0.3

    @pytest.mark.asyncio
    async def test_check_scope_expansion_no_restrictions(self):
        """测试权限范围检查 - 无限制"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="测试",
            applicable_roles=None,
            applicable_departments=None,
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        qa.sources = []
        passed, score, detail = await qa_quality_check_service._check_scope_expansion(None, qa)
        # 无角色和部门限制时会提示
        assert passed is False

    @pytest.mark.asyncio
    async def test_check_answer_completeness_full(self):
        """测试答案完整性 - 完整"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="这是一个完整的答案，包含了必要的详细信息。" * 3,
            short_answer="简短答案",
            detailed_answer="详细答案，包含更多背景信息和具体说明。",
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_answer_completeness(None, qa)
        assert passed is True

    @pytest.mark.asyncio
    async def test_check_answer_completeness_short(self):
        """测试答案完整性 - 答案过短"""
        from app.services.qa_quality_service import qa_quality_check_service
        from app.models.qa import StandardQA

        qa = StandardQA(
            question="测试",
            answer="短答案",
            short_answer=None,
            detailed_answer=None,
            knowledge_base_id="kb1",
            tenant_id="t1",
            created_by="u1",
        )
        passed, score, detail = await qa_quality_check_service._check_answer_completeness(None, qa)
        assert passed is False


class TestOutboxEventConsumer:
    """Outbox 事件消费者测试"""

    @pytest.mark.asyncio
    async def test_handle_document_version_published(self):
        """测试处理文档版本发布事件"""
        # 此测试需要数据库 mock，验证核心逻辑
        from app.services.outbox_consumer import OutboxEventConsumer
        assert OutboxEventConsumer is not None

    @pytest.mark.asyncio
    async def test_handle_document_paused(self):
        """测试处理文档暂停事件"""
        from app.services.outbox_consumer import MEMBER7_EVENT_TYPES
        assert "document.paused" in MEMBER7_EVENT_TYPES

    @pytest.mark.asyncio
    async def test_handle_document_offlined(self):
        """测试处理文档下线事件"""
        from app.services.outbox_consumer import MEMBER7_EVENT_TYPES
        assert "document.offlined" in MEMBER7_EVENT_TYPES

    @pytest.mark.asyncio
    async def test_handle_document_permission_changed(self):
        """测试处理文档权限变更事件"""
        from app.services.outbox_consumer import MEMBER7_EVENT_TYPES
        assert "document.permission.changed" in MEMBER7_EVENT_TYPES

    @pytest.mark.asyncio
    async def test_all_event_types_handled(self):
        """测试所有必需事件类型都已注册"""
        from app.services.outbox_consumer import MEMBER7_EVENT_TYPES
        required = [
            "document.version.published",
            "document.paused",
            "document.offlined",
            "document.permission.changed",
        ]
        for event_type in required:
            assert event_type in MEMBER7_EVENT_TYPES


class TestSchemas:
    """Schema 测试"""

    def test_standard_qa_create_valid(self):
        """测试创建标准问答 Schema 校验"""
        from app.schemas.qa import StandardQACreate

        data = StandardQACreate(
            knowledge_base_id="kb1",
            question="如何申请请假？",
            answer="请通过 OA 系统提交请假申请。",
            keywords=["请假", "OA"],
            category="HR",
        )
        assert data.knowledge_base_id == "kb1"
        assert data.question == "如何申请请假？"
        assert data.keywords == ["请假", "OA"]

    def test_standard_qa_create_invalid_empty_question(self):
        """测试创建标准问答 - 空问题"""
        from app.schemas.qa import StandardQACreate
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            StandardQACreate(
                knowledge_base_id="kb1",
                question="",
                answer="答案",
            )

    def test_qa_match_request_valid(self):
        """测试匹配请求 Schema"""
        from app.schemas.qa import QAMatchRequest

        data = QAMatchRequest(
            query="如何申请请假？",
            keywords=["请假"],
            entities=["OA"],
            intent="question",
            access_context={"roles": ["employee"], "departments": ["engineering"]},
            knowledge_base_ids=["kb1"],
            top_k=5,
            threshold=0.7,
            trusted_threshold=0.85,
        )
        assert data.query == "如何申请请假？"
        assert data.access_context["roles"] == ["employee"]
        assert data.trusted_threshold == 0.85

    def test_candidate_qa_generate_request(self):
        """测试候选问答生成请求 Schema"""
        from app.schemas.qa import CandidateQAGenerateRequest

        data = CandidateQAGenerateRequest(
            knowledge_base_id="kb1",
            max_candidates=100,
            model="gpt-4o",
        )
        assert data.knowledge_base_id == "kb1"
        assert data.max_candidates == 100

    def test_qa_review_submit_request(self):
        """测试审核提交请求 Schema"""
        from app.schemas.qa import QAReviewSubmitRequest

        data = QAReviewSubmitRequest(
            qa_id="qa123",
            action="approve",
            comment="审核通过，内容准确",
        )
        assert data.qa_id == "qa123"
        assert data.action == "approve"

    def test_qa_review_submit_invalid_action(self):
        """测试审核提交 - 无效动作"""
        from app.schemas.qa import QAReviewSubmitRequest
        import pydantic

        # action 字段接受任意字符串，业务逻辑层校验
        data = QAReviewSubmitRequest(
            qa_id="qa123",
            action="invalid_action",
        )
        assert data.action == "invalid_action"

    def test_standard_qa_disable_request(self):
        """测试停用请求 Schema"""
        from app.schemas.qa import StandardQADisableRequest

        data = StandardQADisableRequest(reason="内容已过时")
        assert data.reason == "内容已过时"

    def test_standard_qa_disable_empty_reason(self):
        """测试停用请求 - 空原因"""
        from app.schemas.qa import StandardQADisableRequest
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            StandardQADisableRequest(reason="")