"""
成员5 IndexingService 状态查询适配（成员6只读）。

正式调用：IndexingService.get_index_status(document_version_id)
返回示例：
{
  "document_version_id": "...",
  "opensearch": "completed|failed|pending",
  "pgvector": "completed|failed|pending",
  "opensearch_count": 0,
  "pgvector_count": 0
}
仅当 opensearch 与 pgvector 均为 completed 时，成员6 认为该版本可进入正式召回/发布链路。
"""
from __future__ import annotations

from typing import Any, Protocol


class IndexStatusProvider(Protocol):
    async def get_index_status(self, document_version_id: str) -> dict[str, Any]: ...


def is_dual_index_ready(status: dict[str, Any]) -> bool:
    """双索引均 completed 才可发布/正式检索。"""
    return (
        status.get("opensearch") == "completed"
        and status.get("pgvector") == "completed"
    )
