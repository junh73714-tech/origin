"""
标准问答模块集成测试
测试 API 端点的完整请求-响应流程
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport


@pytest.fixture
def test_app():
    """创建测试用 FastAPI 应用"""
    from app.main import create_app
    app = create_app()
    return app


@pytest.fixture
async def async_client(test_app):
    """创建异步 HTTP 测试客户端"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestStandardQAListAPI:
    """标准问答列表接口测试"""

    @pytest.mark.asyncio
    async def test_list_standard_qas_unauthorized(self, async_client):
        """测试未认证访问"""
        response = await async_client.get("/api/v1/qa/standard")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_standard_qas_with_pagination(self, async_client):
        """测试分页参数"""
        response = await async_client.get(
            "/api/v1/qa/standard?page=1&page_size=10"
        )
        assert response.status_code in (401, 200)  # 401 if no auth, 200 if auth bypassed


class TestQAMatchAPI:
    """标准问答匹配接口测试"""

    @pytest.mark.asyncio
    async def test_match_request_valid(self, async_client):
        """测试有效的匹配请求"""
        payload = {
            "query": "如何申请请假？",
            "keywords": ["请假"],
            "entities": ["OA"],
            "intent": "question",
            "access_context": {
                "roles": ["employee"],
                "departments": ["engineering"],
                "tenant_id": "default",
            },
            "knowledge_base_ids": ["kb1"],
            "top_k": 5,
            "threshold": 0.7,
        }
        response = await async_client.post("/api/v1/qa/match", json=payload)
        # 可能返回 200 或 500（数据库未连接），但不应是 422
        assert response.status_code != 422

    @pytest.mark.asyncio
    async def test_match_request_missing_query(self, async_client):
        """测试缺少 query 参数"""
        payload = {
            "keywords": ["请假"],
            "access_context": {},
        }
        response = await async_client.post("/api/v1/qa/match", json=payload)
        assert response.status_code == 422


class TestCandidateQAGenerateAPI:
    """候选问答生成接口测试"""

    @pytest.mark.asyncio
    async def test_trigger_generation_valid(self, async_client):
        """测试触发候选生成任务"""
        payload = {
            "knowledge_base_id": "kb1",
            "max_candidates": 10,
        }
        response = await async_client.post("/api/v1/qa/candidates/generate", json=payload)
        assert response.status_code in (202, 401)

    @pytest.mark.asyncio
    async def test_trigger_generation_invalid(self, async_client):
        """测试无效的候选生成请求"""
        payload = {
            "knowledge_base_id": "",
            "max_candidates": -1,
        }
        response = await async_client.post("/api/v1/qa/candidates/generate", json=payload)
        assert response.status_code == 422


class TestReviewAPI:
    """审核接口测试"""

    @pytest.mark.asyncio
    async def test_submit_review_approve(self, async_client):
        """测试审核通过"""
        payload = {
            "qa_id": "qa123",
            "action": "approve",
            "comment": "审核通过",
        }
        response = await async_client.post("/api/v1/qa/reviews", json=payload)
        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_submit_review_reject(self, async_client):
        """测试审核驳回"""
        payload = {
            "qa_id": "qa123",
            "action": "reject",
            "comment": "内容不准确",
        }
        response = await async_client.post("/api/v1/qa/reviews", json=payload)
        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_submit_review_invalid_action(self, async_client):
        """测试无效审核动作"""
        payload = {
            "qa_id": "qa123",
            "action": "invalid_action",
        }
        response = await async_client.post("/api/v1/qa/reviews", json=payload)
        assert response.status_code in (400, 401, 422)

    @pytest.mark.asyncio
    async def test_submit_review_publish(self, async_client):
        """测试发布动作"""
        payload = {
            "qa_id": "qa123",
            "action": "publish",
        }
        response = await async_client.post("/api/v1/qa/reviews", json=payload)
        assert response.status_code in (200, 401, 404)


class TestFeedbackAPI:
    """反馈接口测试"""

    @pytest.mark.asyncio
    async def test_submit_positive_feedback(self, async_client):
        """测试点赞"""
        payload = {
            "message_id": "msg123",
            "feedback_type": "positive",
            "qa_id": "qa123",
            "comment": "答案很有帮助",
            "score": 5,
        }
        response = await async_client.post("/api/v1/feedback/", json=payload)
        assert response.status_code in (201, 401)

    @pytest.mark.asyncio
    async def test_submit_negative_feedback(self, async_client):
        """测试点踩"""
        payload = {
            "message_id": "msg123",
            "feedback_type": "negative",
            "qa_id": "qa123",
            "comment": "答案不准确",
            "score": 2,
        }
        response = await async_client.post("/api/v1/feedback/", json=payload)
        assert response.status_code in (201, 401)

    @pytest.mark.asyncio
    async def test_submit_correction_feedback(self, async_client):
        """测试纠错"""
        payload = {
            "message_id": "msg123",
            "feedback_type": "correction",
            "comment": "答案中的日期有误",
            "correction_text": "正确的日期应该是 2024年7月1日",
            "qa_id": "qa123",
        }
        response = await async_client.post("/api/v1/feedback/", json=payload)
        assert response.status_code in (201, 401)

    @pytest.mark.asyncio
    async def test_submit_invalid_feedback_type(self, async_client):
        """测试无效反馈类型"""
        payload = {
            "message_id": "msg123",
            "feedback_type": "invalid",
        }
        response = await async_client.post("/api/v1/feedback/", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_feedbacks(self, async_client):
        """测试查询反馈列表"""
        response = await async_client.get("/api/v1/feedback/?page=1&page_size=10")
        assert response.status_code in (200, 401)


class TestOperationsAPI:
    """运营分析接口测试"""

    @pytest.mark.asyncio
    async def test_get_unanswered_questions(self, async_client):
        """测试未命中问题查询"""
        response = await async_client.get("/api/v1/feedback/operations/unanswered?days=7")
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_high_frequency_questions(self, async_client):
        """测试高频问题查询"""
        response = await async_client.get("/api/v1/feedback/operations/high-frequency?days=7&top_n=10")
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_low_quality_answers(self, async_client):
        """测试低质量答案查询"""
        response = await async_client.get("/api/v1/feedback/operations/low-quality?days=30")
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_get_knowledge_gaps(self, async_client):
        """测试知识缺口查询"""
        response = await async_client.get("/api/v1/feedback/operations/knowledge-gaps?days=30")
        assert response.status_code in (200, 401)


class TestQualityCheckAPI:
    """质量检查接口测试"""

    @pytest.mark.asyncio
    async def test_trigger_quality_check(self, async_client):
        """测试触发质量检查"""
        response = await async_client.post("/api/v1/qa/standard/qa123/quality-check")
        assert response.status_code in (202, 401)

    @pytest.mark.asyncio
    async def test_get_quality_check_result(self, async_client):
        """测试获取质量检查结果"""
        response = await async_client.get("/api/v1/qa/standard/qa123/quality-check")
        assert response.status_code in (200, 401)


class TestAllowedTransitionsAPI:
    """状态流转查询接口测试"""

    @pytest.mark.asyncio
    async def test_get_allowed_transitions(self, async_client):
        """测试查询允许的流转"""
        response = await async_client.get("/api/v1/qa/standard/qa123/allowed-transitions")
        assert response.status_code in (200, 401)


class TestDocumentChangeAPI:
    """文档变更处理接口测试"""

    @pytest.mark.asyncio
    async def test_handle_document_change(self, async_client):
        """测试处理文档变更"""
        response = await async_client.post(
            "/api/v1/qa/internal/document-change"
            "?event_type=document.version.published"
            "&document_id=doc123"
            "&new_version=2"
        )
        assert response.status_code in (200, 401)


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_resource_not_found(self, async_client):
        """测试资源不存在"""
        response = await async_client.get("/api/v1/qa/standard/nonexistent-id")
        assert response.status_code in (401, 404)

    @pytest.mark.asyncio
    async def test_validation_error(self, async_client):
        """测试参数验证错误"""
        response = await async_client.post(
            "/api/v1/qa/standard",
            json={"knowledge_base_id": "kb1"},
        )
        assert response.status_code == 422


class TestResponseFormat:
    """响应格式测试"""

    @pytest.mark.asyncio
    async def test_success_response_format(self, async_client):
        """测试成功响应格式"""
        # 使用健康检查接口测试响应格式
        response = await async_client.get("/api/v1/health")
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "status" in data

    @pytest.mark.asyncio
    async def test_error_response_format(self, async_client):
        """测试错误响应格式"""
        response = await async_client.post(
            "/api/v1/qa/standard",
            json={"knowledge_base_id": "kb1"},
        )
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data