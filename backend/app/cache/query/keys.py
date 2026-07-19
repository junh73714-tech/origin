"""查询/答案缓存键构造。禁止仅用问题文本作为缓存键。"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def build_query_cache_key(
    *,
    tenant_id: str,
    scope_hash: str,
    knowledge_base_ids: list[str],
    document_version_digest: str,
    standard_qa_version: str,
    question_digest: str,
    llm_version: str,
    embedding_version: str,
    reranker_version: str,
    prompt_version: str,
) -> str:
    payload = {
        "tenant_id": tenant_id,
        "scope_hash": scope_hash,
        "kb": sorted(knowledge_base_ids),
        "doc_ver": document_version_digest,
        "qa_ver": standard_qa_version,
        "q": question_digest,
        "llm": llm_version,
        "emb": embedding_version,
        "rerank": reranker_version,
        "prompt": prompt_version,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"qa_cache:{tenant_id}:{scope_hash}:{digest}"


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def digest_versions(versions: list[str]) -> str:
    return digest_text("|".join(sorted(versions)))
