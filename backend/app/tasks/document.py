"""
文档处理 Celery 任务

异步执行文档处理流水线:
- process_document_task: 新文档全流程处理
- process_version_update_task: 版本更新处理
- index_batch_task: 批量索引任务处理
- consistency_check_task: 索引一致性检查

成员5主责: 文档处理Celery任务定义
"""
from celery import Task

from app.core.celery_app import get_celery_app
from app.core.database import get_db_context
from app.core.logging import get_logger

logger = get_logger(__name__)

# 获取Celery应用实例
celery_app = get_celery_app()


class DocumentProcessingTask(Task):
    """文档处理任务基类

    提供自动重试和异常处理。
    """
    max_retries = 3
    default_retry_delay = 60  # 秒

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(
            "celery_task_failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
        )


@celery_app.task(
    bind=True,
    base=DocumentProcessingTask,
    name="tasks.document.process_document",
    max_retries=3,
)
async def process_document_task(
    self, document_id: str, tenant_id: str = "default"
) -> dict:
    """
    处理新文档的Celery任务

    此任务异步执行完整的文档处理流水线:
    解析 -> 清洗 -> 切分 -> Embedding -> 双索引写入
    """
    logger.info("celery_process_document_start", document_id=document_id)

    try:
        async with get_db_context() as db:
            from app.services.orchestrator import DocumentOrchestrator

            orchestrator = DocumentOrchestrator(db)
            result = await orchestrator.process_document(document_id, tenant_id)

            logger.info(
                "celery_process_document_done",
                document_id=document_id,
                chunks=result.get("chunk_count", 0),
            )
            return result

    except Exception as exc:
        logger.error(
            "celery_process_document_failed",
            document_id=document_id,
            error=str(exc),
        )
        # 自动重试
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    base=DocumentProcessingTask,
    name="tasks.document.update_version",
    max_retries=3,
)
async def process_version_update_task(
    self,
    document_id: str,
    version_id: str,
    tenant_id: str = "default",
) -> dict:
    """
    处理文档版本更新的Celery任务

    流程:
    1. 保持旧版本可用
    2. 处理新版本
    3. 增量索引
    4. 准备发布
    """
    logger.info(
        "celery_version_update_start",
        document_id=document_id,
        version_id=version_id,
    )

    try:
        async with get_db_context() as db:
            from app.services.orchestrator import DocumentOrchestrator
            from app.models.document import DocumentVersion
            from sqlalchemy import select

            # 获取版本记录
            result = await db.execute(
                select(DocumentVersion).where(DocumentVersion.id == version_id)
            )
            version = result.scalar_one_or_none()
            if version is None:
                raise ValueError(f"版本不存在: {version_id}")

            orchestrator = DocumentOrchestrator(db)
            result = await orchestrator.update_document_version(
                document_id, tenant_id, version
            )

            logger.info(
                "celery_version_update_done",
                document_id=document_id,
                new_version=version.version,
            )
            return result

    except Exception as exc:
        logger.error(
            "celery_version_update_failed",
            document_id=document_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    base=DocumentProcessingTask,
    name="tasks.document.index_batch",
    max_retries=2,
)
async def index_batch_task(
    self, task_ids: list[str], tenant_id: str = "default"
) -> dict:
    """
    批量索引任务处理

    获取待处理的IndexTask并按序执行索引写入。
    """
    logger.info("celery_index_batch_start", task_count=len(task_ids))

    try:
        async with get_db_context() as db:
            from app.models.document import IndexTask, DocumentChunk, DocumentVersion
            from app.services.indexing import IndexingService
            from sqlalchemy import select

            indexing = IndexingService(db)
            success_count = 0
            failed_count = 0

            for task_id in task_ids:
                result = await db.execute(
                    select(IndexTask).where(IndexTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                if task is None or task.status not in ("pending", "failed"):
                    continue

                try:
                    # 获取关联的Chunk和版本
                    chunk_result = await db.execute(
                        select(DocumentChunk).where(
                            DocumentChunk.document_version_id == task.document_version_id,
                            DocumentChunk.index_status == "pending",
                        ).limit(50)
                    )
                    chunks = list(chunk_result.scalars().all())

                    version_result = await db.execute(
                        select(DocumentVersion).where(
                            DocumentVersion.id == task.document_version_id,
                        )
                    )
                    version = version_result.scalar_one_or_none()

                    if chunks and version:
                        index_result = await indexing.index_chunks_batch(chunks, version)
                        success_count += index_result.get("total", 0)
                        task.status = "completed"
                        task.completed_at = __import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        )
                    else:
                        task.status = "completed"

                    await db.flush()

                except Exception as e:
                    task.status = "failed"
                    task.retry_count = (task.retry_count or 0) + 1
                    task.error_message = str(e)
                    failed_count += 1
                    await db.flush()

            return {
                "total_tasks": len(task_ids),
                "success": success_count,
                "failed": failed_count,
            }

    except Exception as exc:
        logger.error("celery_index_batch_failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    base=DocumentProcessingTask,
    name="tasks.document.consistency_check",
    max_retries=2,
)
async def consistency_check_task(
    self,
    knowledge_base_id: str | None = None,
    auto_fix: bool = False,
    tenant_id: str = "default",
) -> dict:
    """
    索引一致性检查Celery任务

    定期检查OpenSearch和pgvector与PostgreSQL的一致性。
    """
    logger.info(
        "celery_consistency_check_start",
        knowledge_base_id=knowledge_base_id,
        auto_fix=auto_fix,
    )

    try:
        async with get_db_context() as db:
            from app.services.indexing import IndexingService

            indexing = IndexingService(db)
            result = await indexing.consistency_check(
                knowledge_base_id=knowledge_base_id,
                auto_fix=auto_fix,
            )

            logger.info(
                "celery_consistency_check_done",
                total=result.get("total_chunks", 0),
                missing_os=result.get("missing_opensearch", 0),
                missing_pg=result.get("missing_pgvector", 0),
            )
            return result

    except Exception as exc:
        logger.error("celery_consistency_check_failed", error=str(exc))
        raise self.retry(exc=exc)
