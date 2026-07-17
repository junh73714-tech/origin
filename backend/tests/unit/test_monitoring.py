"""
监控模块单元测试（成员7）
测试 Prometheus 指标采集、辅助函数等
"""
import pytest


class TestMonitoringMetrics:
    """监控指标测试"""

    def test_api_metrics_defined(self):
        """测试 API 请求指标已定义"""
        from app.monitoring import api_requests_total, api_request_duration_seconds, api_errors_total

        assert api_requests_total is not None
        assert api_request_duration_seconds is not None
        assert api_errors_total is not None

    def test_llm_metrics_defined(self):
        """测试 LLM 调用指标已定义"""
        from app.monitoring import (
            llm_requests_total,
            llm_request_duration_seconds,
            llm_tokens_total,
        )

        assert llm_requests_total is not None
        assert llm_request_duration_seconds is not None
        assert llm_tokens_total is not None

    def test_retrieval_metrics_defined(self):
        """测试检索指标已定义"""
        from app.monitoring import (
            keyword_retrieval_duration_seconds,
            vector_retrieval_duration_seconds,
            reranker_request_duration_seconds,
        )

        assert keyword_retrieval_duration_seconds is not None
        assert vector_retrieval_duration_seconds is not None
        assert reranker_request_duration_seconds is not None

    def test_qa_metrics_defined(self):
        """测试标准问答指标已定义"""
        from app.monitoring import (
            standard_qa_match_total,
            standard_qa_match_rate,
            standard_qa_refusal_total,
            standard_qa_count_by_status,
        )

        assert standard_qa_match_total is not None
        assert standard_qa_match_rate is not None
        assert standard_qa_refusal_total is not None
        assert standard_qa_count_by_status is not None

    def test_document_metrics_defined(self):
        """测试文档处理指标已定义"""
        from app.monitoring import (
            document_processing_total,
            document_processing_duration_seconds,
            index_task_total,
            index_task_in_progress,
        )

        assert document_processing_total is not None
        assert document_processing_duration_seconds is not None
        assert index_task_total is not None
        assert index_task_in_progress is not None

    def test_user_feedback_metrics_defined(self):
        """测试用户反馈指标已定义"""
        from app.monitoring import user_feedback_total

        assert user_feedback_total is not None

    def test_celery_metrics_defined(self):
        """测试 Celery 指标已定义"""
        from app.monitoring import celery_queue_length, celery_task_total

        assert celery_queue_length is not None
        assert celery_task_total is not None

    def test_service_health_metrics_defined(self):
        """测试服务健康状态指标已定义"""
        from app.monitoring import service_health

        assert service_health is not None

    def test_app_info_defined(self):
        """测试应用信息指标已定义"""
        from app.monitoring import app_info

        assert app_info is not None

    def test_embedding_metrics_defined(self):
        """测试 Embedding 指标已定义"""
        from app.monitoring import embedding_requests_total, embedding_request_duration_seconds

        assert embedding_requests_total is not None
        assert embedding_request_duration_seconds is not None


class TestMonitoringHelpers:
    """监控辅助函数测试"""

    def test_record_api_request(self):
        """测试记录 API 请求指标"""
        from app.monitoring import record_api_request

        # 不应抛出异常
        record_api_request(method="GET", endpoint="/api/v1/health", status_code=200, duration=0.05)

    def test_record_api_error(self):
        """测试记录 API 错误指标"""
        from app.monitoring import record_api_error

        # 不应抛出异常
        record_api_error(method="POST", endpoint="/api/v1/qa/match", error_type="timeout")

    def test_record_llm_call(self):
        """测试记录 LLM 调用指标"""
        from app.monitoring import record_llm_call

        # 不应抛出异常
        record_llm_call(
            provider="openai",
            model="gpt-4o",
            operation="chat",
            duration=1.5,
            input_tokens=500,
            output_tokens=200,
        )

    def test_record_qa_match(self):
        """测试记录标准问答匹配结果"""
        from app.monitoring import record_qa_match

        # 不应抛出异常
        record_qa_match(result="hit")
        record_qa_match(result="miss")

    def test_record_feedback(self):
        """测试记录用户反馈"""
        from app.monitoring import record_feedback

        # 不应抛出异常
        record_feedback(feedback_type="positive")
        record_feedback(feedback_type="negative")

    def test_update_service_health(self):
        """测试更新服务健康状态"""
        from app.monitoring import update_service_health

        # 不应抛出异常
        update_service_health(service_name="postgresql", healthy=True)
        update_service_health(service_name="opensearch", healthy=False)

    def test_init_monitoring(self):
        """测试初始化监控"""
        from app.monitoring import init_monitoring

        # 不应抛出异常
        init_monitoring(app_name="rag-knowledge", app_version="0.1.0")

    def test_update_qa_count_by_status(self):
        """测试更新各状态标准问答数量"""
        from app.monitoring import update_qa_count_by_status

        # 不应抛出异常
        update_qa_count_by_status(status="published", count=50)
        update_qa_count_by_status(status="draft", count=10)

    def test_update_celery_queue_length(self):
        """测试更新 Celery 队列长度"""
        from app.monitoring import update_celery_queue_length

        # 不应抛出异常
        update_celery_queue_length(queue_name="default", length=5)

    def test_record_embedding_call(self):
        """测试记录 Embedding 调用指标"""
        from app.monitoring import record_embedding_call

        # 不应抛出异常
        record_embedding_call(provider="openai", model="text-embedding-3-small", duration=0.3)

    def test_get_metrics(self):
        """测试获取 Prometheus 指标"""
        from app.monitoring import get_metrics

        metrics = get_metrics()
        assert metrics is not None
        assert isinstance(metrics, bytes)
        # 应该包含 Prometheus 格式的指标文本
        assert len(metrics) > 0