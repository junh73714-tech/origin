"""
Provider 模块

成员5主责: EmbeddingProvider 共享实现、OCR Provider 接口
成员6: LLM / Reranker 适配；测试用确定性 Embedding 见 deterministic_embedding
"""
from app.providers.embedding import EmbeddingProvider

__all__ = ["EmbeddingProvider"]
