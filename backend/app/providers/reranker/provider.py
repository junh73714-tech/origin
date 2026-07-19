"""
RerankerProvider 抽象。

正式 Reranker 服务未绑定（硬阻塞）：完成抽象、配置校验、超时/错误边界与测试 Mock。
不得将 Mock 分数伪装为正式生产结果。
"""
from __future__ import annotations

import time
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.retrieval.types import RetrievalHit

logger = get_logger(__name__)


class RerankResult(BaseModel):
    """重排结果。"""

    chunk_id: str
    score: float
    rank: int
    reason: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    model_name: str
    model_version: str
    duration_ms: int = 0
    is_mock: bool = False


class RerankerProvider(Protocol):
    model_name: str
    model_version: str

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalHit],
        top_n: int | None = None,
    ) -> list[RerankResult]: ...


class MockRerankerProvider:
    """
    测试 Mock 重排器：按文本重叠与元数据启发式打分。
    is_mock=True，不得用于正式验收。
    """

    def __init__(
        self,
        model_name: str | None = None,
        model_version: str = "mock-v1",
    ):
        self.model_name = model_name or settings.reranker.model
        self.model_version = model_version
        self.is_bound = False  # 正式服务未绑定

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalHit],
        top_n: int | None = None,
    ) -> list[RerankResult]:
        started = time.perf_counter()
        top_n = top_n or settings.reranker.top_n
        q = query.lower()
        scored: list[RerankResult] = []
        for hit in candidates:
            text = (hit.text_preview or "").lower()
            overlap = sum(1 for token in q.split() if token and token in text)
            entity_bonus = 0.2 if any(t in text for t in q.split() if len(t) > 3) else 0.0
            validity = 0.1 if hit.status == "published" and hit.is_current_version else -1.0
            score = overlap + entity_bonus + validity + float(hit.score or 0) * 0.01
            scored.append(
                RerankResult(
                    chunk_id=hit.chunk_id,
                    score=score,
                    rank=0,
                    reason="mock_heuristic",
                    features={
                        "overlap": overlap,
                        "entity_bonus": entity_bonus,
                        "validity": validity,
                    },
                    model_name=self.model_name,
                    model_version=self.model_version,
                    is_mock=True,
                )
            )
        scored.sort(key=lambda x: -x.score)
        duration_ms = int((time.perf_counter() - started) * 1000)
        results: list[RerankResult] = []
        for idx, item in enumerate(scored[:top_n], start=1):
            item.rank = idx
            item.duration_ms = duration_ms
            results.append(item)
        logger.info(
            "reranker_done",
            model=self.model_name,
            is_mock=True,
            count=len(results),
            duration_ms=duration_ms,
        )
        return results


def get_reranker_provider() -> RerankerProvider:
    """返回 Reranker；真实服务未绑定前使用 Mock。"""
    return MockRerankerProvider()
