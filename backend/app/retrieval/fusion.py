"""结果去重与 Reciprocal Rank Fusion。"""
from __future__ import annotations

from app.retrieval.types import FusedCandidate, RetrievalHit


def dedupe_hits(hits: list[RetrievalHit]) -> list[RetrievalHit]:
    """
    按稳定 chunk_id 去重；同时校验 document_version_id，
    禁止把旧版本内容错误合并到当前版本。
    """
    best: dict[str, RetrievalHit] = {}
    for hit in hits:
        if not hit.is_current_version:
            continue
        if hit.status in {"paused", "offlined", "expired", "draft"}:
            continue
        key = f"{hit.chunk_id}:{hit.document_version_id}"
        existing = best.get(key)
        if existing is None or hit.score > existing.score:
            best[key] = hit
    return list(best.values())


def reciprocal_rank_fusion(
    keyword_hits: list[RetrievalHit],
    vector_hits: list[RetrievalHit],
    k: int = 60,
) -> list[FusedCandidate]:
    """
    标准 RRF：score = sum 1/(k + rank)。
    rank 从 1 开始。参数 k 可配置。
    """
    keyword_hits = [h for h in keyword_hits if h.is_current_version]
    vector_hits = [h for h in vector_hits if h.is_current_version]

    scores: dict[str, FusedCandidate] = {}

    def key_of(hit: RetrievalHit) -> str:
        return f"{hit.chunk_id}:{hit.document_version_id}"

    for rank, hit in enumerate(keyword_hits, start=1):
        dk = key_of(hit)
        cand = scores.get(dk)
        if cand is None:
            cloned = hit.model_copy(deep=True)
            cloned.source = "fused"
            cand = FusedCandidate(
                hit=cloned,
                keyword_rank=rank,
                vector_rank=None,
                rrf_score=0.0,
                dedupe_key=dk,
            )
            scores[dk] = cand
        else:
            cand.keyword_rank = rank
        cand.rrf_score += 1.0 / (k + rank)
        cand.hit.keyword_rank = rank
        cand.hit.rrf_score = cand.rrf_score

    for rank, hit in enumerate(vector_hits, start=1):
        dk = key_of(hit)
        cand = scores.get(dk)
        if cand is None:
            cloned = hit.model_copy(deep=True)
            cloned.source = "fused"
            cand = FusedCandidate(
                hit=cloned,
                keyword_rank=None,
                vector_rank=rank,
                rrf_score=0.0,
                dedupe_key=dk,
            )
            scores[dk] = cand
        else:
            cand.vector_rank = rank
        cand.rrf_score += 1.0 / (k + rank)
        cand.hit.vector_rank = rank
        cand.hit.rrf_score = cand.rrf_score
        cand.hit.score = cand.rrf_score

    fused = sorted(scores.values(), key=lambda c: (-c.rrf_score, c.dedupe_key))
    for idx, cand in enumerate(fused, start=1):
        cand.hit.rank = idx
        cand.hit.score = cand.rrf_score
        cand.hit.source = "fused"
    return fused


def fused_to_hits(candidates: list[FusedCandidate]) -> list[RetrievalHit]:
    """转换为统一 RetrievalHit 列表。"""
    return [c.hit for c in candidates]
