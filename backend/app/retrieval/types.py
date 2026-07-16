"""检索统一结果与过滤语义类型。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RetrievalFilter(BaseModel):
    """与 AccessContext 对齐的检索过滤语义（成员4契约适配）。"""

    tenant_id: str
    knowledge_base_ids: list[str] = Field(default_factory=list)
    department_ids: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    max_confidentiality_level: int = 0
    deny_document_ids: list[str] = Field(default_factory=list)
    allow_document_ids: list[str] = Field(default_factory=list)
    temporary_grant_document_ids: list[str] = Field(default_factory=list)
    require_published: bool = True
    require_current_version: bool = True
    exclude_paused: bool = True
    exclude_offlined: bool = True
    exclude_expired: bool = True
    scope_hash: str = ""

    def to_opensearch_filter(self) -> list[dict[str, Any]]:
        """转换为 OpenSearch bool filter 子句。"""
        filters: list[dict[str, Any]] = [{"term": {"tenant_id": self.tenant_id}}]
        if self.require_published:
            filters.append({"term": {"status": "published"}})
        if self.require_current_version:
            filters.append({"term": {"is_current_version": True}})
        if self.exclude_paused:
            filters.append({"bool": {"must_not": [{"term": {"status": "paused"}}]}})
        if self.exclude_offlined:
            filters.append({"bool": {"must_not": [{"term": {"status": "offlined"}}]}})
        if self.exclude_expired:
            filters.append(
                {
                    "bool": {
                        "should": [
                            {"bool": {"must_not": [{"exists": {"field": "expiration_time"}}]}},
                            {"range": {"expiration_time": {"gt": "now"}}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        # 无任何数据范围且无临时授权时，强制空结果（默认拒绝，召回前生效）
        if (
            not self.knowledge_base_ids
            and not self.allow_document_ids
            and not self.temporary_grant_document_ids
        ):
            filters.append({"terms": {"document_id": ["__no_access__"]}})
            return filters

        if self.knowledge_base_ids:
            filters.append({"terms": {"knowledge_base_id": self.knowledge_base_ids}})
        if self.deny_document_ids:
            filters.append(
                {"bool": {"must_not": [{"terms": {"document_id": self.deny_document_ids}}]}}
            )
        # 允许集合 = 文档白名单 ∪ 临时授权；白名单非空时必须落入该并集
        allow_union = list(
            dict.fromkeys([*self.allow_document_ids, *self.temporary_grant_document_ids])
        )
        if self.allow_document_ids:
            filters.append({"terms": {"document_id": allow_union}})
        elif self.temporary_grant_document_ids and not self.knowledge_base_ids:
            filters.append({"terms": {"document_id": self.temporary_grant_document_ids}})
        if self.max_confidentiality_level >= 0:
            filters.append(
                {
                    "range": {
                        "confidentiality_level": {"lte": self.max_confidentiality_level}
                    }
                }
            )
        return filters

    def to_pgvector_where(self) -> dict[str, Any]:
        """转换为 pgvector/SQL 侧可消费的 WHERE 语义字典。"""
        return {
            "tenant_id": self.tenant_id,
            "knowledge_base_ids": list(self.knowledge_base_ids),
            "deny_document_ids": list(self.deny_document_ids),
            "allow_document_ids": list(self.allow_document_ids),
            "temporary_grant_document_ids": list(self.temporary_grant_document_ids),
            "max_confidentiality_level": self.max_confidentiality_level,
            "require_published": self.require_published,
            "require_current_version": self.require_current_version,
            "exclude_paused": self.exclude_paused,
            "exclude_offlined": self.exclude_offlined,
            "exclude_expired": self.exclude_expired,
            "regions": list(self.regions),
            "project_ids": list(self.project_ids),
            "scope_hash": self.scope_hash,
        }


class RetrievalHit(BaseModel):
    """统一检索候选。"""

    chunk_id: str
    document_id: str
    document_version_id: str
    knowledge_base_id: str = ""
    rank: int = 0
    score: float = 0.0
    source: Literal["keyword", "vector", "fused", "reranked"] = "keyword"
    matched_fields: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    title_path: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    text_preview: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    keyword_rank: int | None = None
    vector_rank: int | None = None
    rrf_score: float | None = None
    is_current_version: bool = True
    status: str = "published"
    confidentiality_level: int = 0


class FusedCandidate(BaseModel):
    """融合后的候选，保留双路排名信息。"""

    hit: RetrievalHit
    keyword_rank: int | None = None
    vector_rank: int | None = None
    rrf_score: float = 0.0
    dedupe_key: str = ""
