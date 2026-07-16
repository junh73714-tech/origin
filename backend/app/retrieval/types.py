"""检索统一结果与过滤语义类型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TemporaryGrantRef(BaseModel):
    """
    临时授权引用，对齐成员4 TemporaryGrantInfo。

    检索过滤仅使用 resource_type=document 的 resource_id；
    保留完整对象以便过期校验与 scope_hash 计算。
    """

    resource_type: str = "document"
    resource_id: str
    permission_type: str = "read"
    effective_time: datetime | None = None
    expiration_time: datetime | None = None

    @field_validator("resource_id")
    @classmethod
    def _require_resource_id(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("resource_id 不能为空")
        return str(v).strip()

    @property
    def document_id(self) -> str | None:
        """文档临时授权时返回文档 ID，否则 None。"""
        if self.resource_type == "document":
            return self.resource_id
        return None


class RetrievalFilter(BaseModel):
    """与 AccessContext / 成员4 RetrievalFilter 对齐的检索过滤语义。"""

    tenant_id: str
    user_id: str = ""
    knowledge_base_ids: list[str] = Field(default_factory=list)
    department_ids: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    max_confidentiality_level: int = 0
    deny_document_ids: list[str] = Field(default_factory=list)
    allow_document_ids: list[str] = Field(default_factory=list)
    # 与成员4 effective_temporary_grants 对齐（对象列表，非纯 ID 列表）
    effective_temporary_grants: list[TemporaryGrantRef] = Field(default_factory=list)
    require_published: bool = True
    require_current_version: bool = True
    exclude_paused: bool = True
    exclude_offlined: bool = True
    exclude_expired: bool = True
    scope_hash: str = ""

    @property
    def temporary_grant_document_ids(self) -> list[str]:
        """从临时授权对象提取文档 ID，供 OpenSearch/pgvector terms 过滤。"""
        ids: list[str] = []
        for g in self.effective_temporary_grants:
            doc_id = g.document_id
            if doc_id and doc_id not in ids:
                ids.append(doc_id)
        return ids

    def to_opensearch_filter(self) -> list[dict[str, Any]]:
        """转换为 OpenSearch bool filter 子句。"""
        temp_doc_ids = self.temporary_grant_document_ids
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
            and not temp_doc_ids
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
        allow_union = list(dict.fromkeys([*self.allow_document_ids, *temp_doc_ids]))
        if self.allow_document_ids:
            filters.append({"terms": {"document_id": allow_union}})
        elif temp_doc_ids and not self.knowledge_base_ids:
            filters.append({"terms": {"document_id": temp_doc_ids}})
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
            "user_id": self.user_id,
            "knowledge_base_ids": list(self.knowledge_base_ids),
            "deny_document_ids": list(self.deny_document_ids),
            "allow_document_ids": list(self.allow_document_ids),
            "temporary_grant_document_ids": list(self.temporary_grant_document_ids),
            "effective_temporary_grants": [
                g.model_dump(mode="json") for g in self.effective_temporary_grants
            ],
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
