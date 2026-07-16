"""会话与消息服务（对接公共契约 /api/v1/qa/*）。"""
from __future__ import annotations

import uuid
from typing import Any

from app.rag.state import RAGState


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class InMemoryConversationStore:
    """
    进程内会话存储，便于无 DB 时的单元/集成测试。
    生产环境应替换为 SQLAlchemy 仓储，写入 Conversation/Message/Citation/QueryLog。
    """

    def __init__(self) -> None:
        self.conversations: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, dict[str, Any]] = {}
        self.citations: dict[str, dict[str, Any]] = {}
        self.queries: dict[str, dict[str, Any]] = {}
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

    def append_turn(
        self,
        *,
        conversation_id: str | None,
        tenant_id: str,
        user_id: str,
        user_content: str,
        state: RAGState,
    ) -> dict[str, Any]:
        if conversation_id and conversation_id in self.conversations:
            conv = self.conversations[conversation_id]
            if conv["user_id"] != user_id:
                raise PermissionError("无权访问会话")
        else:
            conv = self.create_conversation(
                tenant_id=tenant_id, user_id=user_id, title=user_content[:40]
            )

        user_msg_id = new_id("msg")
        asst_msg_id = new_id("msg")
        query_id = new_id("qry")

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
            }

        self.queries[query_id] = {
            "query_id": query_id,
            "conversation_id": conv["id"],
            "message_id": asst_msg_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "state": state.model_dump(),
            "status": "done",
        }
        return {
            "conversation_id": conv["id"],
            "message_id": asst_msg_id,
            "query_id": query_id,
            "user_message_id": user_msg_id,
        }

    def get_citation(self, citation_id: str) -> dict[str, Any] | None:
        return self.citations.get(citation_id)

    def cancel_query(self, query_id: str) -> bool:
        self.cancelled.add(query_id)
        q = self.queries.get(query_id)
        if q:
            q["status"] = "cancelled"
            return True
        return False

    def is_cancelled(self, query_id: str) -> bool:
        return query_id in self.cancelled


default_conversation_store = InMemoryConversationStore()
