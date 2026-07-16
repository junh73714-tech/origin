"""
确定性 Embedding 测试替身（成员6）。

正式生产向量必须使用成员5的 app.providers.embedding.EmbeddingProvider。
本模块仅供成员6单元/集成测试，禁止与生产向量空间混用。
"""
from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.core.config import settings


class EmbeddingProviderProtocol(Protocol):
    model_name: str
    model_version: str
    dimension: int

    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicEmbeddingProvider:
    """确定性伪 Embedding，仅用于单元/集成测试。"""

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
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


def get_embedding_provider() -> EmbeddingProviderProtocol:
    """
    获取 EmbeddingProvider。
    联调阶段可改为返回成员5正式 EmbeddingProvider；当前默认测试替身。
    """
    return DeterministicEmbeddingProvider()
