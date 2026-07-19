"""
Celery 异步任务（成员7）
包含候选问答生成、质量检查、Outbox 事件消费等任务
"""
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)

# Celery 应用实例（延迟初始化）
celery_app = None


def get_celery_app():
    """获取 Celery 应用实例"""
    global celery_app
    if celery_app is None:
        from celery import Celery

        celery_app = Celery(
            "rag_knowledge",
            broker=settings.celery.resolved_broker_url,
            backend=settings.celery.resolved_result_backend,
        )

        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="Asia/Shanghai",
            enable_utc=True,
            task_track_started=True,
            task_acks_late=True,
            worker_prefetch_multiplier=1,
            task_soft_time_limit=600,  # 10分钟软超时
            task_time_limit=900,       # 15分钟硬超时
            task_default_retry_delay=60,
            task_max_retries=3,
        )

        # 自动发现任务
        celery_app.autodiscover_tasks(["app.tasks.qa_tasks"])

    return celery_app


# ============================================================================
# 候选问答生成任务
# ============================================================================

async def generate_candidate_qas(
    knowledge_base_id: str,
    document_ids: list[str] | None = None,
    chunk_ids: list[str] | None = None,
    max_candidates: int = 50,
    model: str | None = None,
    prompt_version: str | None = None,
    user_id: str = "system",
    tenant_id: str = "default",
) -> dict[str, Any]:
    """
    候选问答生成任务
    消费成员5提供的有效文档和 Chunk，生成候选问答
    """
    from app.models.document import Document, DocumentChunk, KnowledgeBase
    from app.services.qa_service import qa_service

    started_at = datetime.now(timezone.utc)

    async with get_db_context() as db:
        # 获取知识库
        from sqlalchemy import select

        kb_stmt = select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.deleted_at.is_(None),
        )
        kb_result = await db.execute(kb_stmt)
        kb = kb_result.scalar_one_or_none()
        if kb is None:
            return {"error": f"知识库 {knowledge_base_id} 不存在", "generated": 0}

        # 获取有效文档和 Chunk
        if document_ids:
            doc_stmt = select(Document).where(
                Document.id.in_(document_ids),
                Document.knowledge_base_id == knowledge_base_id,
                Document.status == "indexed",
                Document.deleted_at.is_(None),
            )
        else:
            doc_stmt = select(Document).where(
                Document.knowledge_base_id == knowledge_base_id,
                Document.status == "indexed",
                Document.deleted_at.is_(None),
            )

        doc_result = await db.execute(doc_stmt)
        documents = list(doc_result.scalars().all())

        if not documents:
            return {"error": "未找到有效文档", "generated": 0}

        # 获取 Chunks
        doc_ids = [d.id for d in documents]
        if chunk_ids:
            chunk_stmt = select(DocumentChunk).where(
                DocumentChunk.id.in_(chunk_ids),
                DocumentChunk.document_id.in_(doc_ids),
                DocumentChunk.index_status == "indexed",
                DocumentChunk.deleted_at.is_(None),
            )
        else:
            chunk_stmt = select(DocumentChunk).where(
                DocumentChunk.document_id.in_(doc_ids),
                DocumentChunk.index_status == "indexed",
                DocumentChunk.deleted_at.is_(None),
            ).limit(max_candidates * 3)

        chunk_result = await db.execute(chunk_stmt)
        chunks = list(chunk_result.scalars().all())

        if not chunks:
            return {"error": "未找到有效 Chunk", "generated": 0}

        generated_count = 0
        session_id = f"gen_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # 按文档分组处理
        doc_chunks: dict[str, list] = {}
        for chunk in chunks:
            if chunk.document_id not in doc_chunks:
                doc_chunks[chunk.document_id] = []
            doc_chunks[chunk.document_id].append(chunk)

        for doc_id, doc_chunk_list in doc_chunks.items():
            if generated_count >= max_candidates:
                break

            doc = next((d for d in documents if d.id == doc_id), None)
            if doc is None:
                continue

            # 对每个 Chunk 生成候选问答
            for chunk in doc_chunk_list[:5]:  # 每个文档最多处理 5 个 Chunk
                if generated_count >= max_candidates:
                    break

                try:
                    candidate_data = await _generate_qa_from_chunk(
                        chunk=chunk,
                        document=doc,
                        knowledge_base_id=knowledge_base_id,
                        model=model or settings.llm.model,
                        prompt_version=prompt_version or "1.0.0",
                        session_id=session_id,
                    )

                    if candidate_data:
                        await qa_service.create_candidate_from_generation(
                            db=db,
                            candidate_data=candidate_data,
                            tenant_id=tenant_id,
                            user_id=user_id,
                        )
                        generated_count += 1

                except Exception as e:
                    logger.error(
                        "candidate_generation_failed",
                        chunk_id=chunk.id,
                        doc_id=doc_id,
                        error=str(e),
                    )
                    continue

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()

        logger.info(
            "candidate_generation_completed",
            knowledge_base_id=knowledge_base_id,
            generated_count=generated_count,
            elapsed_seconds=elapsed,
        )

        return {
            "knowledge_base_id": knowledge_base_id,
            "session_id": session_id,
            "generated": generated_count,
            "documents_processed": len(doc_chunks),
            "chunks_processed": len(chunks),
            "elapsed_seconds": elapsed,
            "model": model or settings.llm.model,
            "prompt_version": prompt_version or "1.0.0",
        }


async def _generate_qa_from_chunk(
    chunk: Any,
    document: Any,
    knowledge_base_id: str,
    model: str,
    prompt_version: str,
    session_id: str,
) -> dict[str, Any] | None:
    """
    从单个 Chunk 生成候选问答
    使用 LLM 生成候选问题、答案、相似问法、关键词等
    """
    content = chunk.content
    if not content or len(content) < 50:
        return None

    # 构建生成提示词
    prompt = _build_qa_generation_prompt(content, document.name)

    try:
        # 调用 LLM 生成
        llm_response = await _call_llm_for_generation(prompt, model)

        if not llm_response:
            return None

        # 解析 LLM 响应
        question = llm_response.get("question", "")
        answer = llm_response.get("answer", "")
        if not question or not answer:
            return None

        return {
            "knowledge_base_id": knowledge_base_id,
            "question": question,
            "short_answer": llm_response.get("short_answer", ""),
            "detailed_answer": llm_response.get("detailed_answer", answer),
            "answer": answer,
            "variants": llm_response.get("variants", []),
            "keywords": llm_response.get("keywords", []),
            "core_entities": llm_response.get("core_entities", []),
            "suggested_roles": llm_response.get("suggested_roles", []),
            "suggested_departments": llm_response.get("suggested_departments", []),
            "source_document_ids": [document.id],
            "source_chunk_ids": [chunk.id],
            "source": "ai_generate",
            "source_session_id": session_id,
            "generation_model": model,
            "generation_prompt_version": prompt_version,
            "confidence": llm_response.get("confidence", 0.7),
            "metadata": {
                "chunk_index": chunk.chunk_index,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "document_name": document.name,
                "document_version": document.current_version,
            },
        }
    except Exception as e:
        logger.error("llm_generation_error", error=str(e))
        return None


def _build_qa_generation_prompt(content: str, document_name: str) -> str:
    """构建候选问答生成提示词"""
    return f"""你是一个知识问答生成专家。请根据以下文档内容，生成标准的问答对。

文档名称: {document_name}
文档内容:
---
{content[:3000]}
---

请生成以下 JSON 格式的问答对（只返回 JSON，不要其他内容）:

{{
    "question": "标准问题（简洁明了，便于检索匹配）",
    "short_answer": "简短答案（一句话回答，不超过100字）",
    "detailed_answer": "详细答案（包含具体细节和依据，引用原文关键信息）",
    "variants": ["相似问法1", "相似问法2", "相似问法3"],
    "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
    "core_entities": ["核心实体1", "核心实体2"],
    "suggested_roles": ["适用角色1", "适用角色2"],
    "suggested_departments": ["适用部门1"],
    "confidence": 0.8
}}

要求:
1. 问题必须基于文档内容，不得编造
2. 答案必须可追溯到原文
3. 相似问法至少3条，覆盖不同问法
4. 关键词至少5个，便于检索
5. 核心实体提取文档中的关键实体（人名、地名、术语、日期等）
6. confidence 为生成置信度 0.0-1.0"""


async def _call_llm_for_generation(
    prompt: str,
    model: str,
) -> dict[str, Any] | None:
    """调用 LLM 进行问答生成"""
    import json

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的知识问答生成助手。你只返回 JSON 格式的结果，不返回其他内容。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        return None

    except Exception as e:
        logger.error("llm_api_call_failed", error=str(e), model=model)
        return None


# ============================================================================
# Outbox 事件消费任务
# ============================================================================

async def consume_outbox_events(batch_size: int = 50) -> dict[str, Any]:
    """
    消费 Outbox 事件的定时任务
    由 Celery Beat 定时调度
    """
    from app.services.outbox_consumer import outbox_event_consumer

    async with get_db_context() as db:
        result = await outbox_event_consumer.consume_events(db, batch_size)

        logger.info(
            "outbox_events_consumed",
            total=result["total"],
            processed=result["processed"],
            failed=result["failed"],
        )

        return result


# ============================================================================
# 质量检查任务
# ============================================================================

async def run_quality_checks(
    qa_id: str,
    candidate_qa_id: str | None = None,
) -> dict[str, Any]:
    """对指定标准问答运行质量检查"""
    from app.models.qa import StandardQA
    from app.services.qa_quality_service import qa_quality_check_service
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with get_db_context() as db:
        stmt = (
            select(StandardQA)
            .where(StandardQA.id == qa_id)
            .options(
                selectinload(StandardQA.sources),
                selectinload(StandardQA.variants),
            )
        )
        result = await db.execute(stmt)
        qa = result.scalar_one_or_none()

        if qa is None:
            return {"error": f"标准问答 {qa_id} 不存在"}

        checks = await qa_quality_check_service.run_all_checks(
            db, qa, candidate_qa_id
        )

        summary = await qa_quality_check_service.get_check_summary(db, qa_id)

        logger.info(
            "quality_checks_completed",
            qa_id=qa_id,
            total=summary["total_checks"],
            passed=summary["passed_checks"],
            failed=summary["failed_checks"],
            overall_pass=summary["overall_pass"],
        )

        return summary


# ============================================================================
# 过期问答自动标记任务
# ============================================================================

async def auto_expire_qas() -> dict[str, Any]:
    """自动标记过期的标准问答"""
    from sqlalchemy import and_, update

    from app.models.qa import QAStatus, StandardQA

    async with get_db_context() as db:
        now = datetime.now(timezone.utc)

        stmt = (
            update(StandardQA)
            .where(
                and_(
                    StandardQA.status == QAStatus.PUBLISHED,
                    StandardQA.effective_end.isnot(None),
                    StandardQA.effective_end < now,
                    StandardQA.deleted_at.is_(None),
                )
            )
            .values(
                status=QAStatus.EXPIRED,
                expired_at=now,
                updated_by="system",
            )
        )
        result = await db.execute(stmt)
        expired_count = result.rowcount

        if expired_count > 0:
            logger.info("auto_expired_qas", count=expired_count)

        return {"expired_count": expired_count}


# ============================================================================
# Celery 任务注册（用于 Celery Beat 定时调度）
# ============================================================================

def register_celery_tasks():
    """注册 Celery 任务"""
    app = get_celery_app()

    @app.task(name="app.tasks.qa_tasks.consume_outbox_events_task")
    def consume_outbox_events_task(batch_size: int = 50):
        """Celery 任务：消费 Outbox 事件"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            consume_outbox_events(batch_size)
        )

    @app.task(name="app.tasks.qa_tasks.auto_expire_qas_task")
    def auto_expire_qas_task():
        """Celery 任务：自动标记过期问答"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(auto_expire_qas())

    return app