"""
EmbeddingProvider 适配层。

正式实现应调用成员5唯一 EmbeddingProvider。此处提供契约一致的本地测试替身，
禁止与生产向量空间混用；维度与模型名必须与配置一致。
"""
from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.core.config import settings


class EmbeddingProvider(Protocol):
    model_name: str
    model_version: str
    dimension: int

    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicEmbeddingProvider:
    """
    确定性伪 Embedding，仅用于单元/集成测试。
    标记：非正式生产实现。
    """

    def __init__(
        self,
        model_name: str | None = None,
        model_version: str = "test-v1",
        dimension: int | None = None,
    ):
        self.model_name = model_name or settings.embedding.model
        self.model_version = model_version
        self.dimension = dimension or settings.embedding.dimension

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(f"{self.model_name}:{self.model_version}:{text}".encode()).digest()
        values: list[float] = []
        while len(values) < self.dimension:
            for b in digest:
                values.append((b / 255.0) * 2 - 1)
                if len(values) >= self.dimension:
                    break
            digest = hashlib.sha256(digest).digest()
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


def get_embedding_provider() -> EmbeddingProvider:
    """
    获取 EmbeddingProvider。
    成员5正式 Provider 就绪后在此替换；当前返回测试替身并保持配置维度一致。
    """
    return DeterministicEmbeddingProvider()
