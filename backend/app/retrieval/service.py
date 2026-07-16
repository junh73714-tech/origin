"""混合检索服务：权限过滤 → Keyword / Vector → 去重 → RRF。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.core.security import AccessContext
from app.retrieval.fusion import dedupe_hits, fused_to_hits, reciprocal_rank_fusion
from app.retrieval.keyword import KeywordRetriever
from app.retrieval.permission_adapter import (
    DefaultPermissionAdapter,
    ensure_access_snapshot,
    filter_hits_before_body,
)
from app.retrieval.types import FusedCandidate, RetrievalFilter, RetrievalHit
from app.retrieval.vector import VectorRetriever

logger = get_logger(__name__)


@dataclass
class HybridRetrievalResult:
    """混合检索输出。"""

    filters: RetrievalFilter
    keyword_hits: list[RetrievalHit] = field(default_factory=list)
    vector_hits: list[RetrievalHit] = field(default_factory=list)
    fused: list[FusedCandidate] = field(default_factory=list)
    fused_hits: list[RetrievalHit] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    timings_ms: dict[str, int] = field(default_factory=dict)


class HybridRetrievalService:
    """权限感知混合检索。"""

    def __init__(
        self,
        keyword: KeywordRetriever,
        vector: VectorRetriever,
        permission: DefaultPermissionAdapter | None = None,
        rrf_k: int = 60,
        allow_partial_degrade: bool = True,
    ):
        self.keyword = keyword
        self.vector = vector
        self.permission = permission or DefaultPermissionAdapter()
        self.rrf_k = rrf_k
        self.allow_partial_degrade = allow_partial_degrade

    def retrieve(
        self,
        query: str,
        access: AccessContext,
        top_k: int = 20,
        mode: str = "hybrid",
    ) -> HybridRetrievalResult:
        access = ensure_access_snapshot(access)
        filters = self.permission.build_retrieval_filters(access)
        result = HybridRetrievalResult(filters=filters)

        keyword_hits: list[RetrievalHit] = []
        vector_hits: list[RetrievalHit] = []

        if mode in {"hybrid", "keyword"}:
            try:
                keyword_hits = self.keyword.search(query, filters, top_k=top_k)
            except Exception as exc:  # noqa: BLE001
                result.errors["keyword"] = str(exc)
                logger.error("keyword_path_failed", error=str(exc))
                if mode == "keyword" or not self.allow_partial_degrade:
                    raise

        if mode in {"hybrid", "vector"}:
            try:
                vector_hits = self.vector.search(query, filters, top_k=top_k)
            except Exception as exc:  # noqa: BLE001
                result.errors["vector"] = str(exc)
                logger.error("vector_path_failed", error=str(exc))
                if mode == "vector" or (
                    mode == "hybrid" and "keyword" in result.errors
                ):
                    raise
                if mode == "hybrid" and not self.allow_partial_degrade:
                    raise

        # 防御性：召回后仍按权限过滤，禁止无权限正文泄漏
        keyword_hits = filter_hits_before_body(keyword_hits, access, self.permission)
        vector_hits = filter_hits_before_body(vector_hits, access, self.permission)
        keyword_hits = dedupe_hits(keyword_hits)
        vector_hits = dedupe_hits(vector_hits)

        result.keyword_hits = keyword_hits
        result.vector_hits = vector_hits

        if mode == "keyword":
            result.fused_hits = keyword_hits
            return result
        if mode == "vector":
            result.fused_hits = vector_hits
            return result

        fused = reciprocal_rank_fusion(keyword_hits, vector_hits, k=self.rrf_k)
        result.fused = fused
        result.fused_hits = fused_to_hits(fused)
        logger.info(
            "hybrid_retrieval_done",
            keyword=len(keyword_hits),
            vector=len(vector_hits),
            fused=len(result.fused_hits),
            scope_hash=filters.scope_hash,
            errors=result.errors,
        )
        return result

    def debug_summary(self, result: HybridRetrievalResult) -> dict[str, Any]:
        """调试摘要，默认不含敏感完整正文。"""
        return {
            "scope_hash": result.filters.scope_hash,
            "filter": result.filters.model_dump(),
            "keyword_count": len(result.keyword_hits),
            "vector_count": len(result.vector_hits),
            "fused_count": len(result.fused_hits),
            "errors": result.errors,
            "keyword_ids": [h.chunk_id for h in result.keyword_hits],
            "vector_ids": [h.chunk_id for h in result.vector_hits],
            "fused_ids": [h.chunk_id for h in result.fused_hits],
        }
