"""RRF 与去重确定性测试。"""
from app.retrieval.fusion import dedupe_hits, reciprocal_rank_fusion
from app.retrieval.types import RetrievalHit


def _hit(chunk: str, doc: str, ver: str, score: float, current: bool = True) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk,
        document_id=doc,
        document_version_id=ver,
        score=score,
        is_current_version=current,
        status="published",
    )


def test_rrf_single_path():
    kw = [_hit("c1", "d1", "v1", 1.0)]
    fused = reciprocal_rank_fusion(kw, [], k=60)
    assert len(fused) == 1
    assert fused[0].keyword_rank == 1
    assert fused[0].vector_rank is None


def test_rrf_overlap():
    kw = [_hit("c1", "d1", "v1", 1.0), _hit("c2", "d2", "v2", 0.9)]
    vec = [_hit("c2", "d2", "v2", 0.8), _hit("c1", "d1", "v1", 0.7)]
    fused = reciprocal_rank_fusion(kw, vec, k=60)
    assert len(fused) == 2
    # 两边都有的应分数更高
    assert fused[0].rrf_score >= fused[1].rrf_score
    assert {f.hit.chunk_id for f in fused} == {"c1", "c2"}


def test_rrf_no_overlap():
    kw = [_hit("c1", "d1", "v1", 1.0)]
    vec = [_hit("c2", "d2", "v2", 1.0)]
    fused = reciprocal_rank_fusion(kw, vec, k=60)
    assert len(fused) == 2


def test_rrf_empty():
    assert reciprocal_rank_fusion([], [], k=60) == []


def test_dedupe_excludes_old_version():
    hits = [
        _hit("c1", "d1", "v_old", 1.0, current=False),
        _hit("c1", "d1", "v_new", 0.5, current=True),
    ]
    out = dedupe_hits(hits)
    assert len(out) == 1
    assert out[0].document_version_id == "v_new"


def test_same_score_stable_order():
    kw = [_hit("c1", "d1", "v1", 1.0), _hit("c2", "d2", "v2", 1.0)]
    fused1 = reciprocal_rank_fusion(kw, [], k=60)
    fused2 = reciprocal_rank_fusion(kw, [], k=60)
    assert [f.hit.chunk_id for f in fused1] == [f.hit.chunk_id for f in fused2]
