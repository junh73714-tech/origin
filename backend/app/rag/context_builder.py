"""上下文组装与 citation_id 生成。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.retrieval.types import RetrievalHit


@dataclass
class ContextSnippet:
    citation_id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    document_name: str
    title_path: str | None
    page_start: int | None
    page_end: int | None
    text: str
    permission_summary: str
    status: str


@dataclass
class AssembledContext:
    snippets: list[ContextSnippet] = field(default_factory=list)
    token_estimate: int = 0
    prompt_block: str = ""


def make_citation_id(
    tenant_id: str,
    document_id: str,
    document_version_id: str,
    chunk_id: str,
) -> str:
    raw = f"{tenant_id}|{document_id}|{document_version_id}|{chunk_id}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"cit_{digest}"


def estimate_tokens(text: str) -> int:
    # 粗略估计：中文约 1.5 字/token
    return max(1, int(len(text) / 1.5))


def assemble_context(
    hits: list[RetrievalHit],
    tenant_id: str,
    token_budget: int = 3000,
    max_per_document: int = 3,
) -> AssembledContext:
    """按文档均衡、Token 预算组装上下文。"""
    # 去重相邻 chunk：同文档同 title_path 合并预览
    selected: list[RetrievalHit] = []
    per_doc: dict[str, int] = {}
    seen_chunk: set[str] = set()
    for hit in hits:
        if hit.chunk_id in seen_chunk:
            continue
        seen_chunk.add(hit.chunk_id)
        count = per_doc.get(hit.document_id, 0)
        if count >= max_per_document:
            continue
        per_doc[hit.document_id] = count + 1
        selected.append(hit)

    snippets: list[ContextSnippet] = []
    used_tokens = 0
    blocks: list[str] = []
    for hit in selected:
        text = hit.text_preview or ""
        cost = estimate_tokens(text) + 32
        if used_tokens + cost > token_budget:
            break
        cid = make_citation_id(
            tenant_id, hit.document_id, hit.document_version_id, hit.chunk_id
        )
        doc_name = (hit.metadata or {}).get("document_name") or hit.document_id
        snip = ContextSnippet(
            citation_id=cid,
            document_id=hit.document_id,
            document_version_id=hit.document_version_id,
            chunk_id=hit.chunk_id,
            document_name=str(doc_name),
            title_path=hit.title_path,
            page_start=hit.page_start,
            page_end=hit.page_end,
            text=text,
            permission_summary=f"status={hit.status};level={hit.confidentiality_level}",
            status=hit.status,
        )
        snippets.append(snip)
        used_tokens += cost
        page = ""
        if hit.page_start is not None:
            page = f" p.{hit.page_start}"
            if hit.page_end and hit.page_end != hit.page_start:
                page += f"-{hit.page_end}"
        blocks.append(
            f"[citation:{cid}] {doc_name} | {hit.title_path or ''}{page}\n{text}"
        )

    return AssembledContext(
        snippets=snippets,
        token_estimate=used_tokens,
        prompt_block="\n\n".join(blocks),
    )
