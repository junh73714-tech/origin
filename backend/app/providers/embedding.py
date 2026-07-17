"""
共享 Embedding Provider

负责文本向量化，是系统唯一的 Embedding 实现。
成员6生成查询向量和成员7生成标准问答向量时必须复用此 Provider。

核心功能:
- 批量文档 Embedding 生成
- 单条查询 Embedding 生成
- 模型名称、维度和版本记录
- 模型变更检测（防止新旧向量混用）

成员5主责: 唯一的 EmbeddingProvider 实现和维护者
"""
import hashlib
import time
from typing import Any

import numpy as np
from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import ModelAPIError
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider:
    """
    共享 Embedding 提供者

    封装 OpenAI 兼容的 Embedding API，支持批量处理和模型版本管理。
    成员6和成员7只能通过此 Provider 生成向量，不得创建第二套配置。

    使用方式:
        provider = EmbeddingProvider()
        vectors = await provider.embed_documents(["文本1", "文本2"])
        query_vector = await provider.embed_query("查询文本")
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        dimension: int | None = None,
        batch_size: int | None = None,
    ):
        """
        初始化 Embedding Provider

        Args:
            model: 模型名称（默认从配置读取）
            api_key: API密钥（默认从配置读取）
            base_url: API基础URL（默认从配置读取）
            dimension: 向量维度（默认从配置读取）
            batch_size: 批处理大小（默认从配置读取）
        """
        embed_config = settings.embedding
        self.model = model or embed_config.model
        self.dimension = dimension or embed_config.dimension
        self.batch_size = batch_size or embed_config.batch_size

        # 生成模型版本标识（基于模型名称和维度）
        self.model_version = self._compute_model_version()

        # 初始化 OpenAI 客户端
        llm_config = settings.llm
        self.client = OpenAI(
            api_key=api_key or llm_config.api_key,
            base_url=base_url or llm_config.base_url,
        )

    def _compute_model_version(self) -> str:
        """计算模型版本标识"""
        raw = f"{self.model}:{self.dimension}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]

    def get_model_info(self) -> dict[str, Any]:
        """
        获取当前模型信息

        成员6/7调用此方法校验模型一致性。

        Returns:
            dict: {"model": str, "dimension": int, "model_version": str}
        """
        return {
            "model": self.model,
            "dimension": self.dimension,
            "model_version": self.model_version,
        }

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成文档 Embedding

        用于文档索引写入，支持大批量文本自动分批处理。

        Args:
            texts: 文本列表

        Returns:
            list[list[float]]: 向量列表，顺序与输入对应
        """
        if not texts:
            return []

        all_vectors: list[list[float]] = []

        # 分批处理
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i: i + self.batch_size]
            batch_vectors = self._embed_batch(batch)
            all_vectors.extend(batch_vectors)

        return all_vectors

    def embed_query(self, text: str) -> list[float]:
        """
        生成查询 Embedding

        成员6用于将用户问题转为查询向量。

        Args:
            text: 查询文本

        Returns:
            list[float]: 查询向量
        """
        if not text or not text.strip():
            raise ModelAPIError(
                message="查询文本为空，无法生成Embedding",
                provider="embedding",
            )

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[text],
            )
            return response.data[0].embedding
        except Exception as e:
            raise ModelAPIError(
                message=f"查询Embedding生成失败: {str(e)}",
                provider="embedding",
                details={"model": self.model, "error": str(e)},
            )

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        生成一批文本的 Embedding

        Args:
            texts: 文本列表（不超过batch_size）

        Returns:
            list[list[float]]: 向量列表
        """
        if not texts:
            return []

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )

                # 按输入顺序返回向量
                vectors = [d.embedding for d in response.data]

                # 维度校验
                for i, v in enumerate(vectors):
                    if len(v) != self.dimension:
                        logger.error(
                            "embedding_dimension_mismatch",
                            expected=self.dimension,
                            actual=len(v),
                            index=i,
                        )
                        raise ModelAPIError(
                            message=f"Embedding维度不匹配: 期望{self.dimension}, 实际{len(v)}",
                            provider="embedding",
                            details={"model": self.model},
                        )

                return vectors

            except ModelAPIError:
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "embedding_retry",
                        attempt=attempt + 1,
                        wait=wait_time,
                        error=str(e),
                    )
                    time.sleep(wait_time)
                else:
                    raise ModelAPIError(
                        message=f"Embedding生成失败（已重试{max_retries}次）: {str(e)}",
                        provider="embedding",
                        details={"model": self.model, "batch_size": len(texts)},
                    )

        return []  # 不可达

    def verify_dimension(self, vectors: list[list[float]]) -> bool:
        """
        校验向量维度是否与当前模型配置一致

        Args:
            vectors: 向量列表

        Returns:
            bool: 维度是否一致
        """
        for v in vectors:
            if len(v) != self.dimension:
                return False
        return True
