"""SSE 事件序列化。契约以 docs/api-contracts.md 为准，并扩展内部调试事件。"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterable


def format_sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def iter_chat_sse(
    *,
    answer: str,
    references: list[dict[str, Any]],
    conversation_id: str,
    message_id: str,
    trace_id: str = "",
    answer_type: str = "rag",
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 24,
) -> Iterable[str]:
    """
    生成符合公共契约的 SSE：
    - event: message （增量/完成）
    - event: done
    同时可发出内部扩展 citation/metadata（成员2可忽略未知事件）。
    """
    yield format_sse(
        "message_start",
        {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "trace_id": trace_id,
            "answer_type": answer_type,
        },
    )
    if not answer:
        answer = ""
    for i in range(0, max(1, len(answer)), chunk_size):
        part = answer[i : i + chunk_size]
        done = i + chunk_size >= len(answer)
        data: dict[str, Any] = {"content": part, "done": done}
        if done:
            data["references"] = references
            data["content"] = answer
        yield format_sse("message", data)
        yield format_sse("answer_delta", {"content": part, "done": done})
    for cit in references:
        yield format_sse("citation", cit)
    yield format_sse(
        "metadata",
        metadata
        or {
            "trace_id": trace_id,
            "answer_type": answer_type,
        },
    )
    yield format_sse(
        "done",
        {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "trace_id": trace_id,
            "answer": answer,
            "answer_type": answer_type,
            "citations": references,
        },
    )


async def aiter_chat_sse(**kwargs: Any) -> AsyncIterator[str]:
    for item in iter_chat_sse(**kwargs):
        yield item
