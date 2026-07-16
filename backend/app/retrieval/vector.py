"""Vector Retrieval（pgvector），复用成员5 EmbeddingProvider。"""
from __future__ import annotations

import math
import time
from typing import Any, Protocol

from app.core.logging import get_logger
from app.retrieval.types import RetrievalFilter, RetrievalHit

logger = get_logger(__name__)


class EmbeddingProviderProtocol(Protocol):
    model_name: str
    model_version: str
    dimension: int

    def embed_query(self, text: str) -> list[float]: ...


class InMemoryVectorStore:
    """测试用内存向量库。"""

    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self.rows = rows or []

    def search(
        self,
        query_vector: list[float],
        where: dict[str, Any],
        top_k: int,
        expected_dim: int,
    ) -> list[tuple[float, dict[str, Any]]]:
        if len(query_vector) != expected_dim:
            raise ValueError(
                f"Embedding 维度不一致: query={len(query_vector)} expected={expected_dim}"
            )
        results: list[tuple[float, dict[str, Any]]] = []
        for row in self.rows:
            if not self._match(row, where):
                continue
            vec = row.get("embedding") or []
            if len(vec) != expected_dim:
                continue
            score = _cosine(query_vector, vec)
            results.append((score, row))
        results.sort(key=lambda x: -x[0])
        return results[:top_k]

    @staticmethod
    def _match(row: dict[str, Any], where: dict[str, Any]) -> bool:
        if row.get("tenant_id") != where.get("tenant_id"):
            return False
        if where.get("require_published") and row.get("status") != "published":
            return False
        if where.get("require_current_version") and not row.get("is_current_version", True):
            return False
        if where.get("exclude_paused") and row.get("status") == "paused":
            return False
        if where.get("exclude_offlined") and row.get("status") == "offlined":
            return False
        deny = set(where.get("deny_document_ids") or [])
        if row.get("document_id") in deny:
            return False
        kb_ids = where.get("knowledge_base_ids") or []
        if kb_ids and row.get("knowledge_base_id") not in kb_ids:
            return False
        max_level = where.get("max_confidentiality_level", 0)
        if int(row.get("confidentiality_level") or 0) > int(max_level):
            return False
        return True


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return dot / (na * nb)


class VectorRetriever:
    """pgvector 向量检索器。"""

    def __init__(
        self,
        embedding_provider: EmbeddingProviderProtocol,
        store: InMemoryVectorStore | None = None,
        timeout_seconds: float = 5.0,
    ):
        self.embedding_provider = embedding_provider
        self.store = store or InMemoryVectorStore()
        self.timeout_seconds = timeout_seconds

    def search(
        self,
        query: str,
        filters: RetrievalFilter,
        top_k: int = 20,
    ) -> list[RetrievalHit]:
        started = time.perf_counter()
        provider = self.embedding_provider
        logger.info(
            "vector_retrieval_start",
            tenant_id=filters.tenant_id,
            model=provider.model_name,
            version=provider.model_version,
            dimension=provider.dimension,
            scope_hash=filters.scope_hash,
        )
        try:
            vector = provider.embed_query(query)
        except Exception as exc:  # noqa: BLE001
            logger.error("embedding_failed", error=str(exc))
            raise
        if len(vector) != provider.dimension:
            raise ValueError(
                f"Embedding 维度不一致: got={len(vector)} expected={provider.dimension}"
            )
        where = filters.to_pgvector_where()
        try:
            raw = self.store.search(
                query_vector=vector,
                where=where,
                top_k=top_k,
                expected_dim=provider.dimension,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("vector_retrieval_failed", error=str(exc))
            raise

        hits: list[RetrievalHit] = []
        for idx, (score, row) in enumerate(raw, start=1):
            hits.append(
                RetrievalHit(
                    chunk_id=row.get("chunk_id") or row.get("id") or "",
                    document_id=row.get("document_id") or "",
                    document_version_id=row.get("document_version_id") or "",
                    knowledge_base_id=row.get("knowledge_base_id") or "",
                    rank=idx,
                    score=float(score),
                    source="vector",
                    matched_fields=["embedding"],
                    title_path=row.get("title_path"),
                    page_start=row.get("page_start"),
                    page_end=row.get("page_end"),
                    text_preview=(row.get("clean_text") or "")[:200],
                    metadata=row.get("metadata") or {},
                    vector_rank=idx,
                    is_current_version=bool(row.get("is_current_version", True)),
                    status=row.get("status") or "published",
                    confidentiality_level=int(row.get("confidentiality_level") or 0),
                )
            )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "vector_retrieval_done",
            count=len(hits),
            duration_ms=elapsed_ms,
            scope_hash=filters.scope_hash,
        )
        return hits
