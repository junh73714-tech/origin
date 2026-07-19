"""
监控模块（成员7）
Prometheus 指标采集、Grafana 看板数据源、关键业务指标埋点
"""
from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, REGISTRY
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# API 请求指标
# ============================================================================

api_requests_total = Counter(
    "rag_api_requests_total",
    "API 请求总数",
    ["method", "endpoint", "status_code"],
)

api_request_duration_seconds = Histogram(
    "rag_api_request_duration_seconds",
    "API 请求耗时（秒）",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

api_errors_total = Counter(
    "rag_api_errors_total",
    "API 错误总数",
    ["method", "endpoint", "error_type"],
)

# ============================================================================
# LLM 调用指标
# ============================================================================

llm_requests_total = Counter(
    "rag_llm_requests_total",
    "LLM 调用总数",
    ["provider", "model", "operation"],
)

llm_request_duration_seconds = Histogram(
    "rag_llm_request_duration_seconds",
    "LLM 调用耗时（秒）",
    ["provider", "model", "operation"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    "rag_llm_tokens_total",
    "LLM Token 使用总数",
    ["provider", "model", "type"],  # type: input / output
)

# ============================================================================
# Embedding 调用指标
# ============================================================================

embedding_requests_total = Counter(
    "rag_embedding_requests_total",
    "Embedding 调用总数",
    ["provider", "model"],
)

embedding_request_duration_seconds = Histogram(
    "rag_embedding_request_duration_seconds",
    "Embedding 调用耗时（秒）",
    ["provider", "model"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# ============================================================================
# Reranker 指标
# ============================================================================

reranker_request_duration_seconds = Histogram(
    "rag_reranker_request_duration_seconds",
    "Reranker 调用耗时（秒）",
    ["provider", "model"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

# ============================================================================
# 检索指标
# ============================================================================

keyword_retrieval_duration_seconds = Histogram(
    "rag_keyword_retrieval_duration_seconds",
    "关键词检索耗时（秒）",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

vector_retrieval_duration_seconds = Histogram(
    "rag_vector_retrieval_duration_seconds",
    "向量检索耗时（秒）",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# ============================================================================
# 文档处理指标
# ============================================================================

document_processing_total = Counter(
    "rag_document_processing_total",
    "文档处理总数",
    ["status"],  # status: success / failed
)

document_processing_duration_seconds = Histogram(
    "rag_document_processing_duration_seconds",
    "文档处理耗时（秒）",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# ============================================================================
# 索引任务指标
# ============================================================================

index_task_total = Counter(
    "rag_index_task_total",
    "索引任务总数",
    ["task_type", "status"],
)

index_task_in_progress = Gauge(
    "rag_index_task_in_progress",
    "进行中的索引任务数",
)

# ============================================================================
# 标准问答指标
# ============================================================================

standard_qa_match_total = Counter(
    "rag_standard_qa_match_total",
    "标准问答匹配总数",
    ["result"],  # result: hit / miss
)

standard_qa_match_rate = Gauge(
    "rag_standard_qa_match_rate",
    "标准问答命中率",
)

standard_qa_refusal_total = Counter(
    "rag_standard_qa_refusal_total",
    "拒答总数",
)

standard_qa_count_by_status = Gauge(
    "rag_standard_qa_count_by_status",
    "各状态标准问答数量",
    ["status"],
)

# ============================================================================
# 用户反馈指标
# ============================================================================

user_feedback_total = Counter(
    "rag_user_feedback_total",
    "用户反馈总数",
    ["feedback_type"],  # positive / negative / correction
)

# ============================================================================
# Celery 指标
# ============================================================================

celery_queue_length = Gauge(
    "rag_celery_queue_length",
    "Celery 队列长度",
    ["queue_name"],
)

celery_task_total = Counter(
    "rag_celery_task_total",
    "Celery 任务总数",
    ["task_name", "status"],
)

# ============================================================================
# 服务健康状态
# ============================================================================

service_health = Gauge(
    "rag_service_health",
    "关键服务健康状态（1=健康, 0=不健康）",
    ["service_name"],
)

# ============================================================================
# 应用信息
# ============================================================================

app_info = Info(
    "rag_app_info",
    "应用信息",
)


def init_monitoring(app_name: str, app_version: str) -> None:
    """初始化监控指标"""
    app_info.info({
        "name": app_name,
        "version": app_version,
    })
    logger.info("monitoring_initialized", app_name=app_name, app_version=app_version)


def get_metrics() -> bytes:
    """获取 Prometheus 指标"""
    return generate_latest(REGISTRY)


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus 指标端点"""
    return PlainTextResponse(
        content=get_metrics(),
        media_type="text/plain; charset=utf-8",
    )


# ============================================================================
# 指标采集辅助函数
# ============================================================================

def record_api_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """记录 API 请求指标"""
    api_requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    api_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_api_error(method: str, endpoint: str, error_type: str) -> None:
    """记录 API 错误指标"""
    api_errors_total.labels(method=method, endpoint=endpoint, error_type=error_type).inc()


def record_llm_call(provider: str, model: str, operation: str, duration: float, input_tokens: int, output_tokens: int) -> None:
    """记录 LLM 调用指标"""
    llm_requests_total.labels(provider=provider, model=model, operation=operation).inc()
    llm_request_duration_seconds.labels(provider=provider, model=model, operation=operation).observe(duration)
    llm_tokens_total.labels(provider=provider, model=model, type="input").inc(input_tokens)
    llm_tokens_total.labels(provider=provider, model=model, type="output").inc(output_tokens)


def record_embedding_call(provider: str, model: str, duration: float) -> None:
    """记录 Embedding 调用指标"""
    embedding_requests_total.labels(provider=provider, model=model).inc()
    embedding_request_duration_seconds.labels(provider=provider, model=model).observe(duration)


def record_qa_match(result: str) -> None:
    """记录标准问答匹配结果"""
    standard_qa_match_total.labels(result=result).inc()


def record_feedback(feedback_type: str) -> None:
    """记录用户反馈"""
    user_feedback_total.labels(feedback_type=feedback_type).inc()


def update_service_health(service_name: str, healthy: bool) -> None:
    """更新服务健康状态"""
    service_health.labels(service_name=service_name).set(1 if healthy else 0)


def update_qa_count_by_status(status: str, count: int) -> None:
    """更新各状态标准问答数量"""
    standard_qa_count_by_status.labels(status=status).set(count)


def update_celery_queue_length(queue_name: str, length: int) -> None:
    """更新 Celery 队列长度"""
    celery_queue_length.labels(queue_name=queue_name).set(length)