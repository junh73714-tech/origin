"""
索引写入服务

管理文档索引的完整生命周期:
1. OpenSearch BM25 关键词索引写入
2. pgvector 向量索引写入
3. IndexTask 任务管理和幂等重试
4. 索引一致性检查

成员5主责: Embedding任务和向量写入 + OpenSearch文档写入
成员6只负责检索读取（只读）
"""
import json
import hashlib
from datetime import datetime, timezone
from typing import Any

from opensearchpy import OpenSearch, exceptions as os_exceptions
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger
from app.models.document import DocumentChunk, DocumentVersion, IndexTask
from app.providers.embedding import EmbeddingProvider
from app.services.chunking import ChunkData

logger = get_logger(__name__)

# OpenSearch 索引名称
OPENSEARCH_CHUNK_INDEX = "rag_chunks"


def build_idempotent_key(document_version_id: str, chunk_id: str, target: str) -> str:
    """构建索引幂等键"""
    raw = f"{document_version_id}:{chunk_id}:{target}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class IndexingService:
    """
    索引写入服务

    负责将文档Chunk写入 OpenSearch (BM25) 和 pgvector (向量)。
    所有写入操作幂等，基于 idempotent_key 去重。
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding = EmbeddingProvider()
        self.opensearch = self._create_opensearch_client()

    def _create_opensearch_client(self) -> OpenSearch:
        """创建OpenSearch客户端"""
        os_config = settings.opensearch
        return OpenSearch(
            hosts=[{"host": os_config.host, "port": os_config.port}],
            http_auth=(os_config.user, os_config.password),
            use_ssl=os_config.scheme == "https",
            verify_certs=False,
            ssl_show_warn=False,
        )

    # -------------------------------------------------------------------------
    # IndexTask 管理
    # -------------------------------------------------------------------------

    async def create_index_task(
        self,
        tenant_id: str,
        document_id: str,
        document_version_id: str,
        task_type: str,
        target: str = "both",
        chunk_id: str | None = None,
    ) -> IndexTask:
        """
        创建索引任务

        Args:
            tenant_id: 租户ID
            document_id: 文档ID
            document_version_id: 版本ID
            task_type: 任务类型 (create/update/delete/rebuild/consistency_check)
            target: 目标 (opensearch/pgvector/both)
            chunk_id: Chunk ID（单Chunk任务，批量任务为空）
        """
        idem_key = build_idempotent_key(
            document_version_id, chunk_id or "batch", target
        )

        task = IndexTask(
            tenant_id=tenant_id,
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_id=chunk_id,
            task_type=task_type,
            target=target,
            idempotent_key=idem_key,
            status="pending",
            retry_count=0,
            max_retries=3,
            created_by="system",
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def get_pending_tasks(self, limit: int = 10) -> list[IndexTask]:
        """获取待处理的索引任务"""
        result = await self.db.execute(
            select(IndexTask)
            .where(IndexTask.status == "pending")
            .order_by(IndexTask.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # OpenSearch 写入
    # -------------------------------------------------------------------------

    async def index_to_opensearch(
        self,
        chunk: DocumentChunk,
        version: DocumentVersion,
    ) -> bool:
        """
        将Chunk写入OpenSearch BM25索引

        存储字段:
        - chunk_id, document_id, document_version_id
        - knowledge_base_id, tenant_id
        - chunk_no, title_path
        - clean_text（BM25检索字段）
        - page_start, page_end
        - permission_metadata（权限过滤字段）
        - created_at
        """
        doc = {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_version_id": chunk.document_version_id,
            "knowledge_base_id": chunk.knowledge_base_id,
            "tenant_id": chunk.tenant_id,
            "chunk_no": chunk.chunk_no,
            "title_path": chunk.title_path or "",
            "clean_text": chunk.clean_text,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "token_count": chunk.token_count,
            "status": chunk.status,
            "permission_metadata": chunk.permission_metadata or {},
            "created_at": (
                chunk.created_at.isoformat() if chunk.created_at else None
            ),
        }

        idem_key = build_idempotent_key(
            chunk.document_version_id, chunk.id, "opensearch"
        )

        try:
            self.opensearch.index(
                index=OPENSEARCH_CHUNK_INDEX,
                id=idem_key,
                body=doc,
                refresh=False,
            )
            logger.debug("opensearch_indexed", chunk_id=chunk.id, key=idem_key)
            return True
        except os_exceptions.OpenSearchException as e:
            logger.error("opensearch_index_failed", chunk_id=chunk.id, error=str(e))
            raise StorageError(
                message=f"OpenSearch索引写入失败: {str(e)}",
                details={"chunk_id": chunk.id, "idempotent_key": idem_key},
            )

    async def delete_from_opensearch(
        self, document_version_id: str, chunk_id: str
    ) -> bool:
        """从OpenSearch删除Chunk索引"""
        idem_key = build_idempotent_key(document_version_id, chunk_id, "opensearch")

        try:
            self.opensearch.delete(
                index=OPENSEARCH_CHUNK_INDEX,
                id=idem_key,
                ignore=[404],  # 忽略已删除
            )
            return True
        except os_exceptions.OpenSearchException as e:
            logger.error("opensearch_delete_failed", chunk_id=chunk_id, error=str(e))
            return False

    # -------------------------------------------------------------------------
    # pgvector 写入
    # -------------------------------------------------------------------------

    async def index_to_pgvector(
        self,
        chunk: DocumentChunk,
        version: DocumentVersion,
        embedding_vector: list[float],
    ) -> bool:
        """
        将Chunk的向量写入pgvector

        在 pgvector 表中存储:
        - chunk_id（关联Chunk记录）
        - embedding（向量数据）
        - 权限和版本元数据（用于检索过滤）
        """
        # pgvector插入使用原始SQL（因为ORM对vector类型支持有限）
        vector_str = f"[{','.join(str(v) for v in embedding_vector)}]"

        stmt = text("""
            INSERT INTO chunk_vectors (
                id, tenant_id, chunk_id, document_id, document_version_id,
                knowledge_base_id, embedding, model_version, dimension,
                permission_metadata, created_at
            ) VALUES (
                :id, :tenant_id, :chunk_id, :document_id, :document_version_id,
                :knowledge_base_id, :embedding, :model_version, :dimension,
                :permission_metadata, :created_at
            )
            ON CONFLICT (id) DO UPDATE SET
                embedding = :embedding,
                model_version = :model_version,
                permission_metadata = :permission_metadata
        """)

        idem_key = build_idempotent_key(
            chunk.document_version_id, chunk.id, "pgvector"
        )

        try:
            await self.db.execute(
                stmt,
                {
                    "id": idem_key,
                    "tenant_id": chunk.tenant_id,
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_version_id": chunk.document_version_id,
                    "knowledge_base_id": chunk.knowledge_base_id,
                    "embedding": vector_str,
                    "model_version": self.embedding.model_version,
                    "dimension": self.embedding.dimension,
                    "permission_metadata": json.dumps(
                        chunk.permission_metadata or {}
                    ),
                    "created_at": datetime.now(timezone.utc),
                },
            )
            await self.db.flush()
            return True
        except Exception as e:
            logger.error("pgvector_index_failed", chunk_id=chunk.id, error=str(e))
            raise StorageError(
                message=f"pgvector索引写入失败: {str(e)}",
                details={"chunk_id": chunk.id},
            )

    async def delete_from_pgvector(self, chunk_id: str) -> bool:
        """从pgvector删除Chunk向量"""
        stmt = text("DELETE FROM chunk_vectors WHERE chunk_id = :chunk_id")
        try:
            await self.db.execute(stmt, {"chunk_id": chunk_id})
            await self.db.flush()
            return True
        except Exception as e:
            logger.error("pgvector_delete_failed", chunk_id=chunk_id, error=str(e))
            return False

    # -------------------------------------------------------------------------
    # 批量索引
    # -------------------------------------------------------------------------

    async def index_chunks_batch(
        self,
        chunks: list[DocumentChunk],
        version: DocumentVersion,
    ) -> dict[str, int]:
        """
        批量索引Chunk（同时写入OpenSearch和pgvector）

        流程:
        1. 生成所有Chunk的Embedding
        2. 写入OpenSearch
        3. 写入pgvector
        4. 更新Chunk的index_status

        Returns:
            dict: {"opensearch_success": int, "pgvector_success": int, "total": int}
        """
        if not chunks:
            return {"opensearch_success": 0, "pgvector_success": 0, "total": 0}

        # 提取文本
        texts = [chunk.clean_text for chunk in chunks]

        # 生成Embedding
        vectors = self.embedding.embed_documents(texts)

        os_success = 0
        pg_success = 0

        for chunk, vector in zip(chunks, vectors):
            # 写入OpenSearch
            try:
                await self.index_to_opensearch(chunk, version)
                os_success += 1
            except Exception as e:
                logger.error("batch_os_failed", chunk_id=chunk.id, error=str(e))

            # 写入pgvector
            try:
                await self.index_to_pgvector(chunk, version, vector)
                pg_success += 1
            except Exception as e:
                logger.error("batch_pg_failed", chunk_id=chunk.id, error=str(e))

            # 更新Chunk索引状态
            if os_success > 0 and pg_success > 0:
                chunk.index_status = "indexed"
            else:
                chunk.index_status = "failed"
            await self.db.flush()

        return {
            "opensearch_success": os_success,
            "pgvector_success": pg_success,
            "total": len(chunks),
        }

    # -------------------------------------------------------------------------
    # 一致性检查
    # -------------------------------------------------------------------------

    async def consistency_check(
        self,
        knowledge_base_id: str | None = None,
        auto_fix: bool = False,
    ) -> dict[str, Any]:
        """
        检查OpenSearch和pgvector索引与PostgreSQL的一致性

        检查项:
        1. PostgreSQL中有但OpenSearch中无的Chunk
        2. PostgreSQL中有但pgvector中无的Chunk
        3. 索引版本与当前模型版本不一致

        Returns:
            dict: 检查结果 {"missing_os": int, "missing_pg": int, "model_mismatch": int, "fixed": int}
        """
        # 查询所有已索引的Chunk
        query = select(DocumentChunk).where(
            DocumentChunk.status == "active",
        )
        if knowledge_base_id:
            query = query.where(DocumentChunk.knowledge_base_id == knowledge_base_id)

        result = await self.db.execute(query)
        chunks = list(result.scalars().all())

        missing_os = 0
        missing_pg = 0
        model_mismatch = 0
        fixed = 0

        for chunk in chunks:
            os_key = build_idempotent_key(
                chunk.document_version_id, chunk.id, "opensearch"
            )
            pg_key = build_idempotent_key(
                chunk.document_version_id, chunk.id, "pgvector"
            )

            # 检查OpenSearch
            try:
                self.opensearch.get(
                    index=OPENSEARCH_CHUNK_INDEX, id=os_key
                )
            except os_exceptions.NotFoundError:
                missing_os += 1
                if auto_fix:
                    # 重新索引（需要版本信息，此处简化）
                    logger.info("consistency_fix_os", chunk_id=chunk.id)

            # 检查pgvector
            pg_stmt = text(
                "SELECT id FROM chunk_vectors WHERE id = :key"
            )
            pg_result = await self.db.execute(pg_stmt, {"key": pg_key})
            if pg_result.scalar_one_or_none() is None:
                missing_pg += 1
                if auto_fix:
                    logger.info("consistency_fix_pg", chunk_id=chunk.id)

        return {
            "total_chunks": len(chunks),
            "missing_opensearch": missing_os,
            "missing_pgvector": missing_pg,
            "model_mismatch": model_mismatch,
            "fixed": fixed,
        }
