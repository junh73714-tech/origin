"""会话与消息服务（对接公共契约 /api/v1/qa/*）。"""
from __future__ import annotations

import uuid
from typing import Any

from app.rag.state import RAGState


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class InMemoryConversationStore:
    """
    进程内会话/日志存储。
    结构对齐 Citation/QueryLog/RetrievalLog；生产可替换为 SQLAlchemy 仓储写库。
    """

    def __init__(self) -> None:
        self.conversations: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, dict[str, Any]] = {}
        self.citations: dict[str, dict[str, Any]] = {}
        self.queries: dict[str, dict[str, Any]] = {}
        self.query_logs: dict[str, dict[str, Any]] = {}
        self.retrieval_logs: list[dict[str, Any]] = []
        self.cancelled: set[str] = set()

    def create_conversation(
        self,
        *,
        tenant_id: str,
        user_id: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        cid = new_id("cnv")
        row = {
            "id": cid,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "title": title or "新会话",
            "status": "active",
            "messages": [],
        }
        self.conversations[cid] = row
        return row

    def list_conversations(self, user_id: str, tenant_id: str) -> list[dict[str, Any]]:
        return [
            c
            for c in self.conversations.values()
            if c["user_id"] == user_id and c["tenant_id"] == tenant_id
        ]

    def get_conversation(self, conversation_id: str, user_id: str) -> dict[str, Any] | None:
        c = self.conversations.get(conversation_id)
        if not c or c["user_id"] != user_id:
            return None
        msgs = [self.messages[mid] for mid in c["messages"] if mid in self.messages]
        return {**c, "messages": msgs}

    def begin_query(
        self,
        *,
        tenant_id: str,
        user_id: str,
        conversation_id: str | None,
        original_query: str,
        scope_hash: str,
        trace_id: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """查询开始即分配 query_id，支持中途取消。"""
        if conversation_id and conversation_id in self.conversations:
            conv = self.conversations[conversation_id]
            if conv["user_id"] != user_id or conv["tenant_id"] != tenant_id:
                raise PermissionError("无权访问会话")
        else:
            conv = self.create_conversation(
                tenant_id=tenant_id, user_id=user_id, title=original_query[:40]
            )
        query_id = new_id("qry")
        self.queries[query_id] = {
            "query_id": query_id,
            "conversation_id": conv["id"],
            "user_id": user_id,
            "tenant_id": tenant_id,
            "status": "running",
            "original_query": original_query,
        }
        self.query_logs[query_id] = {
            "query_id": query_id,
            "conversation_id": conv["id"],
            "user_id": user_id,
            "tenant_id": tenant_id,
            "original_query": original_query,
            "scope_hash": scope_hash,
            "trace_id": trace_id,
            "request_id": request_id,
            "cache_hit": False,
            "status": "running",
        }
        return {"query_id": query_id, "conversation_id": conv["id"]}

    def append_turn(
        self,
        *,
        conversation_id: str | None,
        tenant_id: str,
        user_id: str,
        user_content: str,
        state: RAGState,
        query_id: str | None = None,
        cache_hit: bool = False,
    ) -> dict[str, Any]:
        if conversation_id and conversation_id in self.conversations:
            conv = self.conversations[conversation_id]
            if conv["user_id"] != user_id:
                raise PermissionError("无权访问会话")
        else:
            conv = self.create_conversation(
                tenant_id=tenant_id, user_id=user_id, title=user_content[:40]
            )

        if not query_id:
            started = self.begin_query(
                tenant_id=tenant_id,
                user_id=user_id,
                conversation_id=conv["id"],
                original_query=user_content,
                scope_hash=str(state.access_context.get("scope_hash") or ""),
                trace_id=state.trace_id,
            )
            query_id = started["query_id"]
            conv = self.conversations[started["conversation_id"]]

        user_msg_id = new_id("msg")
        asst_msg_id = new_id("msg")
        user_msg = {
            "id": user_msg_id,
            "conversation_id": conv["id"],
            "role": "user",
            "content": user_content,
        }
        asst_msg = {
            "id": asst_msg_id,
            "conversation_id": conv["id"],
            "role": "assistant",
            "content": state.generated_answer,
            "intent": state.intent,
            "confidence": state.confidence,
            "references": state.citations,
            "metadata": {
                "answer_type": state.answer_type,
                "trace_id": state.trace_id,
                "refusal_reason": state.refusal_reason,
                "query_id": query_id,
                "cache_hit": cache_hit,
            },
        }
        self.messages[user_msg_id] = user_msg
        self.messages[asst_msg_id] = asst_msg
        conv["messages"].extend([user_msg_id, asst_msg_id])

        for cit in state.citations:
            cid = cit.get("citation_id") or new_id("cit")
            self.citations[cid] = {
                **cit,
                "citation_id": cid,
                "message_id": asst_msg_id,
                "tenant_id": tenant_id,
                "query_id": query_id,
                "quote_text": cit.get("quote") or cit.get("quote_text"),
                "document_version_id": cit.get("document_version")
                or cit.get("document_version_id"),
                "source_status": cit.get("source_status") or cit.get("status") or "published",
            }

        # RetrievalLog
        for stage, rows in (
            ("keyword", state.keyword_results),
            ("vector", state.vector_results),
            ("rrf", state.fused_results),
            ("rerank", state.reranked_results),
        ):
            self.retrieval_logs.append(
                {
                    "query_id": query_id,
                    "tenant_id": tenant_id,
                    "stage": stage,
                    "hit_count": len(rows or []),
                    "latency_ms": (state.timings_ms or {}).get(stage)
                    or (state.timings_ms or {}).get("retrieval"),
                    "details": {"ids": [r.get("chunk_id") for r in (rows or [])[:20]]},
                }
            )

        qlog = self.query_logs.get(query_id) or {}
        qlog.update(
            {
                "rewritten_query": state.rewritten_query,
                "intent": state.intent,
                "answer_type": state.answer_type,
                "refusal_reason": state.refusal_reason,
                "cache_hit": cache_hit,
                "status": "cancelled" if state.cancelled else "done",
                "latency_ms": sum((state.timings_ms or {}).values()),
                "debug": state.debug,
            }
        )
        self.query_logs[query_id] = qlog
        self.queries[query_id] = {
            **self.queries.get(query_id, {}),
            "query_id": query_id,
            "conversation_id": conv["id"],
            "message_id": asst_msg_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "state": state.model_dump(),
            "status": qlog["status"],
            "user_content": user_content,
        }
        return {
            "conversation_id": conv["id"],
            "message_id": asst_msg_id,
            "query_id": query_id,
            "user_message_id": user_msg_id,
        }

    def append_cached_turn(
        self,
        *,
        conversation_id: str | None,
        tenant_id: str,
        user_id: str,
        user_content: str,
        cached: dict[str, Any],
        trace_id: str,
        scope_hash: str,
        query_id: str | None = None,
    ) -> dict[str, Any]:
        """缓存命中：不跑图，直接落库会话与 QueryLog。"""
        state = RAGState(
            user_id=user_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            original_query=user_content,
            rewritten_query=user_content,
            generated_answer=cached.get("answer", ""),
            answer_type=cached.get("answer_type", "rag"),
            citations=list(cached.get("citations") or []),
            access_context={"scope_hash": scope_hash},
            trace_id=trace_id,
            evidence_status="cache_hit",
        )
        return self.append_turn(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_content=user_content,
            state=state,
            query_id=query_id,
            cache_hit=True,
        )

    def get_citation(self, citation_id: str) -> dict[str, Any] | None:
        return self.citations.get(citation_id)

    def get_query(self, query_id: str) -> dict[str, Any] | None:
        return self.queries.get(query_id)

    def get_message(self, message_id: str) -> dict[str, Any] | None:
        return self.messages.get(message_id)

    def history_texts(self, conversation_id: str | None, user_id: str, limit: int = 6) -> list[str]:
        if not conversation_id:
            return []
        conv = self.get_conversation(conversation_id, user_id)
        if not conv:
            return []
        texts = [m["content"] for m in conv.get("messages", []) if m.get("role") == "user"]
        return texts[-limit:]

    def cancel_query(self, query_id: str, user_id: str, tenant_id: str) -> bool:
        q = self.queries.get(query_id)
        if not q or q.get("user_id") != user_id or q.get("tenant_id") != tenant_id:
            return False
        self.cancelled.add(query_id)
        q["status"] = "cancelled"
        if query_id in self.query_logs:
            self.query_logs[query_id]["status"] = "cancelled"
        return True

    def is_cancelled(self, query_id: str) -> bool:
        return query_id in self.cancelled


default_conversation_store = InMemoryConversationStore()
