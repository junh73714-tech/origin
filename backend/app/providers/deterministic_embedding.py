"""
确定性 Embedding 测试替身（成员6）。

正式生产向量必须使用成员5的 app.providers.embedding.EmbeddingProvider。
本模块仅供成员6单元/集成测试，禁止与生产向量空间混用。

联调开关：环境变量 USE_MEMBER5_EMBEDDING=1 时返回成员5正式实现。
"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Any, Protocol

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


class Member5EmbeddingAdapter:
    """
    包装成员5 EmbeddingProvider，统一暴露 model_name 属性供检索日志使用。
    embed_query / embed_documents 为同步调用（与成员5实现一致）。
    """

    def __init__(self, provider: Any = None):
        from app.providers.embedding import EmbeddingProvider

        self._inner = provider or EmbeddingProvider()
        self.model_name = getattr(self._inner, "model", None) or settings.embedding.model
        self.model_version = getattr(self._inner, "model_version", "") or ""
        self.dimension = int(getattr(self._inner, "dimension", settings.embedding.dimension))

    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)


def get_embedding_provider() -> EmbeddingProviderProtocol:
    """
    获取 EmbeddingProvider。
    - USE_MEMBER5_EMBEDDING=1：成员5正式实现（联调/生产）
    - 默认：确定性测试替身（单元测试）
    """
    flag = os.getenv("USE_MEMBER5_EMBEDDING", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return Member5EmbeddingAdapter()
    return DeterministicEmbeddingProvider()
