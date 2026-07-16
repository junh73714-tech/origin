"""Keyword Retrieval（OpenSearch BM25），权限过滤在召回前注入。"""
from __future__ import annotations

import time
from typing import Any, Protocol

from app.core.logging import get_logger
from app.retrieval.types import RetrievalFilter, RetrievalHit

logger = get_logger(__name__)


class OpenSearchClientProtocol(Protocol):
    def search(self, index: str, body: dict[str, Any]) -> dict[str, Any]: ...


class InMemoryKeywordIndex:
    """测试用内存索引，语义与 OpenSearch 过滤对齐。"""

    def __init__(self, docs: list[dict[str, Any]] | None = None):
        self.docs = docs or []

    def search(self, index: str, body: dict[str, Any]) -> dict[str, Any]:
        del index
        query_text = ""
        try:
            query_text = body["query"]["bool"]["must"][0]["multi_match"]["query"]
        except (KeyError, IndexError, TypeError):
            query_text = ""
        filters = body.get("query", {}).get("bool", {}).get("filter", [])
        size = int(body.get("size", 10))

        def match_filters(doc: dict[str, Any]) -> bool:
            for f in filters:
                if "term" in f:
                    field, value = next(iter(f["term"].items()))
                    if doc.get(field) != value:
                        return False
                if "terms" in f:
                    field, values = next(iter(f["terms"].items()))
                    if doc.get(field) not in values:
                        return False
                if "bool" in f and "must_not" in f["bool"]:
                    for mn in f["bool"]["must_not"]:
                        if "term" in mn:
                            field, value = next(iter(mn["term"].items()))
                            if doc.get(field) == value:
                                return False
                        if "terms" in mn:
                            field, values = next(iter(mn["terms"].items()))
                            if doc.get(field) in values:
                                return False
                if "range" in f:
                    field, cond = next(iter(f["range"].items()))
                    val = doc.get(field, 0)
                    if "lte" in cond and val > cond["lte"]:
                        return False
            return True

        hits = []
        q = query_text.lower()
        for doc in self.docs:
            if not match_filters(doc):
                continue
            text = (doc.get("clean_text") or doc.get("raw_text") or "").lower()
            title = (doc.get("title_path") or "").lower()
            score = 0.0
            matched: list[str] = []
            if q and q in text:
                score += 2.0
                matched.append("content")
            if q and q in title:
                score += 1.5
                matched.append("title")
            # 精确编号加权
            if q and q.replace("-", "") in text.replace("-", ""):
                score += 1.0
                matched.append("exact_id")
            if score <= 0 and not q:
                score = 0.1
            if score > 0:
                hits.append((score, doc, matched))
        hits.sort(key=lambda x: -x[0])
        return {
            "hits": {
                "hits": [
                    {
                        "_score": s,
                        "_source": d,
                        "highlight": {"clean_text": [d.get("clean_text", "")[:120]]},
                        "matched_fields": m,
                    }
                    for s, d, m in hits[:size]
                ]
            }
        }


class KeywordRetriever:
    """OpenSearch Keyword 检索器。"""

    def __init__(
        self,
        client: OpenSearchClientProtocol | None = None,
        index_name: str = "document_chunks",
        timeout_seconds: float = 5.0,
    ):
        self.client = client or InMemoryKeywordIndex()
        self.index_name = index_name
        self.timeout_seconds = timeout_seconds

    def build_query(
        self,
        query: str,
        filters: RetrievalFilter,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """构造带权限过滤的 BM25 查询（过滤在召回前）。"""
        return {
            "size": top_k,
            "timeout": f"{int(self.timeout_seconds * 1000)}ms",
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "title_path^3",
                                    "clean_text^2",
                                    "raw_text",
                                    "entities^2",
                                    "tags",
                                ],
                                "type": "best_fields",
                            }
                        }
                    ],
                    "filter": filters.to_opensearch_filter(),
                }
            },
            "highlight": {"fields": {"clean_text": {}, "title_path": {}}},
        }

    def search(
        self,
        query: str,
        filters: RetrievalFilter,
        top_k: int = 20,
    ) -> list[RetrievalHit]:
        started = time.perf_counter()
        body = self.build_query(query, filters, top_k=top_k)
        logger.info(
            "keyword_retrieval_start",
            tenant_id=filters.tenant_id,
            scope_hash=filters.scope_hash,
            top_k=top_k,
        )
        try:
            raw = self.client.search(self.index_name, body)
        except Exception as exc:  # noqa: BLE001
            logger.error("keyword_retrieval_failed", error=str(exc))
            raise
        hits: list[RetrievalHit] = []
        for idx, item in enumerate(raw.get("hits", {}).get("hits", []), start=1):
            src = item.get("_source", {})
            hl = item.get("highlight", {})
            highlights: list[str] = []
            for v in hl.values():
                if isinstance(v, list):
                    highlights.extend(v)
            hit = RetrievalHit(
                chunk_id=src.get("chunk_id") or src.get("id") or "",
                document_id=src.get("document_id") or "",
                document_version_id=src.get("document_version_id") or "",
                knowledge_base_id=src.get("knowledge_base_id") or "",
                rank=idx,
                score=float(item.get("_score") or 0.0),
                source="keyword",
                matched_fields=list(item.get("matched_fields") or []),
                highlights=highlights,
                title_path=src.get("title_path"),
                page_start=src.get("page_start"),
                page_end=src.get("page_end"),
                text_preview=(src.get("clean_text") or "")[:200],
                metadata=src.get("metadata") or {},
                keyword_rank=idx,
                is_current_version=bool(src.get("is_current_version", True)),
                status=src.get("status") or "published",
                confidentiality_level=int(src.get("confidentiality_level") or 0),
            )
            hits.append(hit)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "keyword_retrieval_done",
            count=len(hits),
            duration_ms=elapsed_ms,
            scope_hash=filters.scope_hash,
        )
        return hits
