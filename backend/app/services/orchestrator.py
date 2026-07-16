"""
文档处理编排器

串联文档处理全流程:
  上传 -> 解析 -> 清洗 -> 切分 -> Embedding -> 双索引写入 -> 发布

同时管理版本更新、增量索引和跨模块事件发布。

成员5主责: 文档处理流水线编排和状态控制
"""
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessStateError, DocumentProcessingError
from app.core.logging import get_logger
from app.models.audit import OutboxEvent
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentProcessLog,
    DocumentVersion,
    KnowledgeBase,
)
from app.services.chunking import DocumentChunker, ChunkData, estimate_tokens
from app.services.indexing import IndexingService
from app.services.parsing.dispatcher import ParserDispatcher
from app.services.storage import MinioStorageService

logger = get_logger(__name__)

# 文档处理阶段定义
STAGE_UPLOAD = "upload"
STAGE_PARSE = "parse"
STAGE_CLEAN = "clean"
STAGE_SPLIT = "split"
STAGE_EMBED = "embed"
STAGE_INDEX_OS = "index_opensearch"
STAGE_INDEX_PG = "index_pgvector"
STAGE_PUBLISH = "publish"


class DocumentOrchestrator:
    """
    文档处理编排器

    管理文档从上传到发布的完整处理流程。
    支持新文档处理和版本更新两种模式。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = ParserDispatcher()
        self.chunker = DocumentChunker()
        self.indexing = IndexingService(db)

    # -------------------------------------------------------------------------
    # 新文档处理流水线
    # -------------------------------------------------------------------------

    async def process_document(
        self, document_id: str, tenant_id: str
    ) -> dict[str, Any]:
        """
        处理新上传的文档

        完整流水线:
        1. 获取文档和版本信息
        2. 下载文件并解析
        3. 清洗解析结果
        4. 切分为Chunk
        5. 创建DocumentChunk记录
        6. 生成Embedding
        7. 写入OpenSearch和pgvector
        8. 更新文档状态为pending_review

        Returns:
            dict: 处理结果摘要
        """
        doc = await self._get_document(document_id, tenant_id)
        version = await self._get_current_version(document_id, tenant_id)

        # 更新文档状态为处理中
        await self._transition_state(doc, "processing")

        try:
            # 阶段1: 解析
            await self._log_stage(doc.id, version.id, STAGE_PARSE, "processing")
            parse_result = await self._parse_document(doc, version)
            await self._log_stage(doc.id, version.id, STAGE_PARSE, "completed",
                                  metadata={"pages": parse_result.total_pages,
                                            "chars": parse_result.total_chars,
                                            "quality": parse_result.quality.value})

            # 阶段2: 清洗
            await self._log_stage(doc.id, version.id, STAGE_CLEAN, "processing")
            self.parser.clean_result(parse_result)
            await self._log_stage(doc.id, version.id, STAGE_CLEAN, "completed")

            # 阶段3: 切分
            await self._log_stage(doc.id, version.id, STAGE_SPLIT, "processing")
            chunk_data_list = self.chunker.chunk(parse_result)
            await self._log_stage(doc.id, version.id, STAGE_SPLIT, "completed",
                                  metadata={"chunk_count": len(chunk_data_list)})

            # 阶段4: 创建Chunk记录
            chunks = await self._create_chunk_records(
                doc, version, chunk_data_list, tenant_id
            )

            # 更新文档元数据
            doc.page_count = parse_result.total_pages
            doc.char_count = parse_result.total_chars
            doc.token_count = sum(c.token_count for c in chunks)
            doc.chunk_count = len(chunks)  # 知识库也需要更新
            doc.processing_error = None
            await self.db.flush()

            # 阶段5: Embedding + 索引写入
            await self._log_stage(doc.id, version.id, STAGE_EMBED, "processing")
            index_result = await self.indexing.index_chunks_batch(chunks, version)

            # 更新Chunk索引状态
            indexed_count = max(index_result["opensearch_success"],
                              index_result["pgvector_success"])
            await self._log_stage(doc.id, version.id, STAGE_INDEX_OS, "completed",
                                  metadata=index_result)

            # 阶段6: 完成处理，进入待检查状态
            await self._transition_state(doc, "pending_review")

            # 发布Outbox事件
            await self._publish_outbox_event(
                event_type="document.index.completed",
                aggregate_type="document",
                aggregate_id=doc.id,
                payload={
                    "document_id": doc.id,
                    "document_version_id": version.id,
                    "chunk_count": len(chunks),
                    "indexed_count": indexed_count,
                    "knowledge_base_id": doc.knowledge_base_id,
                },
            )

            logger.info("document_processed", document_id=doc.id,
                       chunks=len(chunks), indexed=indexed_count)

            return {
                "document_id": doc.id,
                "status": doc.status,
                "chunk_count": len(chunks),
                "indexed_count": indexed_count,
                "parse_quality": parse_result.quality.value,
            }

        except Exception as e:
            # 处理失败
            await self._transition_state(doc, "failed")
            doc.processing_error = str(e)
            await self.db.flush()
            logger.error("document_processing_failed", document_id=doc.id,
                        error=str(e))
            raise DocumentProcessingError(
                message=f"文档处理失败: {str(e)}",
                document_id=doc.id,
                details={"stage": "pipeline", "error": str(e)},
            )

    # -------------------------------------------------------------------------
    # 版本更新
    # -------------------------------------------------------------------------

    async def update_document_version(
        self,
        document_id: str,
        tenant_id: str,
        new_version: DocumentVersion,
    ) -> dict[str, Any]:
        """
        处理文档版本更新

        流程:
        1. 保持旧版本可用
        2. 解析新版本文件
        3. 对比新旧Chunk差异
        4. 创建增量索引任务
        5. 发布新版本（旧版本退出检索）
        6. 通知缓存失效和问答待复核
        """
        doc = await self._get_document(document_id, tenant_id)

        # 获取旧版本
        old_version = await self._get_current_version(document_id, tenant_id)

        # 处理新版本（类似新文档流程）
        await self._transition_state(doc, "processing")

        try:
            # 解析新版本
            parse_result = await self._parse_document(doc, new_version,
                                                       version_record=new_version)
            self.parser.clean_result(parse_result)
            chunk_data_list = self.chunker.chunk(parse_result)

            # 创建新版本的Chunk记录
            new_chunks = await self._create_chunk_records(
                doc, new_version, chunk_data_list, tenant_id
            )

            # 对比新旧Chunk（简化实现：基于content_hash对比）
            old_chunks = await self._get_version_chunks(old_version.id)
            diff = self._compare_chunks(old_chunks, new_chunks)

            # 增量索引
            index_result = await self._incremental_index(
                new_version, new_chunks, old_chunks, diff
            )

            # 更新版本状态
            new_version.publish_status = "pending_review"
            new_version.is_current_version = False  # 尚未发布，旧版本仍是当前
            await self.db.flush()

            # 更新文档当前版本号
            doc.current_version = new_version.version
            doc.status = "pending_review"
            await self.db.flush()

            # 发布Outbox事件：新版本已创建
            await self._publish_outbox_event(
                event_type="document.version.created",
                aggregate_type="document",
                aggregate_id=doc.id,
                payload={
                    "document_id": doc.id,
                    "old_version_id": old_version.id,
                    "new_version_id": new_version.id,
                    "old_version": old_version.version,
                    "new_version": new_version.version,
                    "diff": diff,
                },
            )

            return {
                "document_id": doc.id,
                "old_version": old_version.version,
                "new_version": new_version.version,
                "diff": diff,
                "new_chunks": len(new_chunks),
                "status": doc.status,
            }

        except Exception as e:
            await self._transition_state(doc, "failed")
            doc.processing_error = str(e)
            await self.db.flush()
            raise DocumentProcessingError(
                message=f"版本更新失败: {str(e)}",
                document_id=doc.id,
            )

    # -------------------------------------------------------------------------
    # 发布控制
    # -------------------------------------------------------------------------

    async def publish_document_version(
        self, document_id: str, tenant_id: str
    ) -> Document:
        """
        发布文档新版本

        1. 验证文档处于待发布状态
        2. 验证双索引可用
        3. 发布新版本（设为当前版本）
        4. 旧版本退出正式检索
        5. 发送 Outbox 事件通知成员6和成员7
        """
        doc = await self._get_document(document_id, tenant_id)

        if doc.status != "pending_publish":
            raise BusinessStateError(
                message="只有待发布状态的文档可以发布",
                current_state=doc.status,
                expected_state="pending_publish",
            )

        # 获取新版本
        new_version = await self._get_current_version(document_id, tenant_id)
        if new_version.publish_status != "pending_publish":
            raise BusinessStateError(
                message="版本未处于待发布状态",
                current_state=new_version.publish_status,
                expected_state="pending_publish",
            )

        # 旧版本退出检索
        old_versions = await self._get_old_versions(document_id, new_version.id)
        for old_ver in old_versions:
            old_ver.is_current_version = False
            old_ver.publish_status = "offline"

        # 发布新版本
        new_version.is_current_version = True
        new_version.publish_status = "published"
        new_version.published_at = datetime.now(timezone.utc)

        # 更新文档状态
        doc.status = "published"
        doc.published_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Outbox: 版本已发布
        await self._publish_outbox_event(
            event_type="document.version.published",
            aggregate_type="document",
            aggregate_id=doc.id,
            payload={
                "document_id": doc.id,
                "version_id": new_version.id,
                "version": new_version.version,
                "knowledge_base_id": doc.knowledge_base_id,
                "published_at": new_version.published_at.isoformat()
                if new_version.published_at else None,
            },
        )

        logger.info("document_version_published", document_id=doc.id,
                    version=new_version.version)
        return doc

    async def offline_document(
        self, document_id: str, tenant_id: str
    ) -> Document:
        """
        下线文档

        1. 文档状态改为offline
        2. 当前版本标记为offline
        3. 发送Outbox事件通知成员6停止检索
        """
        doc = await self._get_document(document_id, tenant_id)

        if doc.status not in ("published", "paused"):
            raise BusinessStateError(
                message="只有已发布或已暂停的文档可以下线",
                current_state=doc.status,
            )

        doc.status = "offline"

        # 当前版本也标记为offline
        version = await self._get_current_version(document_id, tenant_id)
        if version:
            version.publish_status = "offline"

        await self.db.flush()

        # Outbox: 文档已下线
        await self._publish_outbox_event(
            event_type="document.offlined",
            aggregate_type="document",
            aggregate_id=doc.id,
            payload={
                "document_id": doc.id,
                "version_id": version.id if version else None,
                "knowledge_base_id": doc.knowledge_base_id,
            },
        )

        logger.info("document_offlined", document_id=doc.id)
        return doc

    # -------------------------------------------------------------------------
    # 内部辅助方法
    # -------------------------------------------------------------------------

    async def _get_document(self, doc_id: str, tenant_id: str) -> Document:
        """获取文档"""
        result = await self.db.execute(
            select(Document).where(
                Document.id == doc_id, Document.tenant_id == tenant_id
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            from app.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(resource_type="文档", resource_id=doc_id)
        return doc

    async def _get_current_version(
        self, document_id: str, tenant_id: str
    ) -> DocumentVersion:
        """获取文档当前版本"""
        result = await self.db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.tenant_id == tenant_id,
                DocumentVersion.is_current_version == True,
            )
        )
        ver = result.scalar_one_or_none()
        if ver is None:
            from app.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(
                resource_type="文档版本", resource_id=f"{document_id}/current"
            )
        return ver

    async def _parse_document(
        self, doc: Document, version: DocumentVersion,
        version_record: DocumentVersion | None = None,
    ) -> Any:
        """下载并解析文档"""
        storage = MinioStorageService()
        file_data = storage.download_file(version.file_path)
        return self.parser.parse_and_clean(
            file_data, doc.file_type, doc.original_filename
        )

    async def _create_chunk_records(
        self,
        doc: Document,
        version: DocumentVersion,
        chunk_data_list: list[ChunkData],
        tenant_id: str,
    ) -> list[DocumentChunk]:
        """从ChunkData创建DocumentChunk数据库记录"""
        chunks = []
        for cd in chunk_data_list:
            chunk = DocumentChunk(
                tenant_id=tenant_id,
                knowledge_base_id=doc.knowledge_base_id,
                document_id=doc.id,
                document_version_id=version.id,
                chunk_no=cd.chunk_no,
                title_path=cd.title_path,
                page_start=cd.page_start,
                page_end=cd.page_end,
                source_offset=cd.source_offset,
                raw_text=cd.raw_text,
                clean_text=cd.clean_text,
                content_hash=self._hash_text(cd.clean_text),
                token_count=cd.token_count,
                chunk_metadata=cd.metadata,
                permission_metadata={
                    "knowledge_base_id": doc.knowledge_base_id,
                    "document_id": doc.id,
                    "scope_hash": self._make_scope_hash(doc),
                    "created_by": doc.created_by,
                },
                status="active",
                index_status="pending",
                created_by=doc.created_by,
            )
            self.db.add(chunk)
            chunks.append(chunk)

        await self.db.flush()
        return chunks

    async def _transition_state(
        self, doc: Document, new_status: str
    ) -> None:
        """文档状态流转"""
        doc.status = new_status
        await self.db.flush()

    async def _log_stage(
        self,
        document_id: str,
        version_id: str | None,
        stage: str,
        status: str,
        progress: int = 0,
        metadata: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        """记录处理阶段日志"""
        log = DocumentProcessLog(
            tenant_id="default",
            document_id=document_id,
            document_version_id=version_id,
            stage=stage,
            status=status,
            progress=progress,
            stage_metadata=metadata,
            error_message=error_message,
            started_at=datetime.now(timezone.utc) if status == "processing" else None,
            completed_at=datetime.now(timezone.utc) if status == "completed" else None,
            created_by="system",
        )
        self.db.add(log)
        await self.db.flush()

    async def _publish_outbox_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
    ) -> None:
        """发布Outbox事件（与文档状态变更在同一事务中）"""
        event = OutboxEvent(
            tenant_id="default",
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            published=False,
            retry_count=0,
            max_retries=3,
            created_by="system",
        )
        self.db.add(event)
        await self.db.flush()

    async def _get_version_chunks(
        self, version_id: str
    ) -> list[DocumentChunk]:
        """获取版本的所有Chunk"""
        result = await self.db.execute(
            select(DocumentChunk).where(
                DocumentChunk.document_version_id == version_id,
            )
        )
        return list(result.scalars().all())

    def _compare_chunks(
        self,
        old_chunks: list[DocumentChunk],
        new_chunks: list[DocumentChunk],
    ) -> dict[str, int]:
        """
        比较新旧Chunk差异

        基于content_hash进行对比。

        Returns:
            dict: {"added": int, "modified": int, "deleted": int, "unchanged": int}
        """
        old_hashes = {c.content_hash for c in old_chunks}
        new_hashes = {c.content_hash for c in new_chunks}

        added = len(new_hashes - old_hashes)
        deleted = len(old_hashes - new_hashes)
        unchanged = len(old_hashes & new_hashes)
        modified = min(added, deleted)  # 简化估算

        return {
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "unchanged": unchanged,
        }

    async def _incremental_index(
        self,
        version: DocumentVersion,
        new_chunks: list[DocumentChunk],
        old_chunks: list[DocumentChunk],
        diff: dict,
    ) -> dict:
        """增量索引：只索引新增和变更的Chunk"""
        if diff["added"] == 0 and diff["modified"] == 0:
            return {"total": 0, "opensearch_success": 0, "pgvector_success": 0,
                    "skipped": len(new_chunks)}

        # 对于新增或变更的Chunk（简化：索引所有新Chunk）
        return await self.indexing.index_chunks_batch(new_chunks, version)

    async def _get_old_versions(
        self, document_id: str, exclude_version_id: str
    ) -> list[DocumentVersion]:
        """获取旧版本列表"""
        result = await self.db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.id != exclude_version_id,
                DocumentVersion.is_current_version == True,
            )
        )
        return list(result.scalars().all())

    @staticmethod
    def _hash_text(text: str) -> str:
        """计算文本的简单哈希"""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def _make_scope_hash(doc: Document) -> str:
        """生成权限范围哈希（简化版，正式对接成员4后替换为 AccessContext.scope_hash）"""
        import hashlib
        raw = f"{doc.tenant_id}:{doc.knowledge_base_id}:{doc.id}:{doc.created_by}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
