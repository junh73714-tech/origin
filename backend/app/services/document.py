"""
文档业务服务

提供文档上传、管理、发布控制、版本管理功能。
文档上传流程: 校验 -> 哈希 -> 存储 -> 创建记录 -> 创建版本 -> 触发异步处理

成员5主责：文档完整生命周期管理
"""
import os
from datetime import datetime, timezone
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BusinessStateError,
    ResourceNotFoundError,
    StorageError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentVersion,
    IndexTask,
    KnowledgeBase,
)
from app.schemas.common import PaginationParams
from app.schemas.document import (
    DocumentListParams,
)
from app.services.storage import (
    MinioStorageService,
    build_storage_key,
    calculate_sha256,
    validate_file,
)

logger = get_logger(__name__)


class DocumentService:
    """文档业务服务

    负责文档上传、查询、状态管理和版本控制。
    依赖:
    - KnowledgeBaseService: 知识库验证
    - MinioStorageService: 文件存储
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = MinioStorageService()

    # -------------------------------------------------------------------------
    # 知识库验证（内部使用）
    # -------------------------------------------------------------------------

    async def _verify_knowledge_base(self, kb_id: str, tenant_id: str) -> KnowledgeBase:
        """验证知识库存在且可用"""
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise ResourceNotFoundError(resource_type="知识库", resource_id=kb_id)
        if kb.status != "active":
            raise BusinessStateError(
                message="知识库已停用，无法上传文档",
                current_state=kb.status,
                expected_state="active",
            )
        return kb

    # -------------------------------------------------------------------------
    # 文档上传
    # -------------------------------------------------------------------------

    async def upload_document(
        self,
        tenant_id: str,
        user_id: str,
        knowledge_base_id: str,
        filename: str,
        file_data: bytes,
        mime_type: str | None = None,
    ) -> Document:
        """
        上传单个文档

        流程:
        1. 验证知识库状态
        2. 校验文件格式和大小
        3. 计算SHA-256哈希
        4. 检测重复文件
        5. 构建存储路径
        6. 上传到MinIO
        7. 创建文档记录和初始版本记录
        """
        file_size = len(file_data)

        # 1. 验证知识库
        await self._verify_knowledge_base(knowledge_base_id, tenant_id)

        # 2. 文件安全校验
        validate_file(filename, file_size, mime_type)

        # 3. 计算哈希
        file_hash = calculate_sha256(file_data)

        # 4. 检测重复文件（同一知识库内）
        existing = await self.db.execute(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.knowledge_base_id == knowledge_base_id,
                Document.file_hash == file_hash,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(
                message="相同内容的文件已存在于此知识库中",
                details={"knowledge_base_id": knowledge_base_id, "file_hash": file_hash},
            )

        # 5. 创建文档记录
        ext = os.path.splitext(filename)[1].lower()
        doc = Document(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            name=filename,
            original_filename=filename,
            file_type=ext.lstrip("."),
            mime_type=mime_type or "application/octet-stream",
            file_size=file_size,
            file_hash=file_hash,
            file_path="",  # 待上传后更新
            status="draft",
            current_version=1,
            created_by=user_id,
        )
        self.db.add(doc)
        await self.db.flush()  # 获取 doc.id

        # 6. 构建存储路径并上传
        storage_key = build_storage_key(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            document_id=doc.id,
            version=1,
            file_hash=file_hash,
            extension=ext,
        )

        try:
            upload_result = self.storage.upload_file(
                file_data=file_data,
                storage_key=storage_key,
                content_type=mime_type,
            )
            doc.file_path = storage_key
        except StorageError:
            # 上传失败时回滚：清理已创建的文档记录
            await self.db.rollback()
            raise

        # 7. 创建初始版本记录
        version = DocumentVersion(
            tenant_id=tenant_id,
            document_id=doc.id,
            knowledge_base_id=knowledge_base_id,
            version=1,
            file_path=storage_key,
            file_size=file_size,
            file_hash=file_hash,
            previous_version=None,
            is_current_version=True,
            change_summary="初始版本",
            publish_status="draft",
            created_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()

        # 更新知识库文档计数
        await self._increment_kb_document_count(knowledge_base_id, tenant_id)

        logger.info(
            "document_uploaded",
            document_id=doc.id,
            name=filename,
            size=file_size,
            hash=file_hash,
            key=storage_key,
        )
        return doc

    async def upload_document_stream(
        self,
        tenant_id: str,
        user_id: str,
        knowledge_base_id: str,
        filename: str,
        file_stream: BinaryIO,
        file_size: int,
        file_hash: str,
        mime_type: str | None = None,
    ) -> Document:
        """
        流式上传文档（适用于大文件）

        与 upload_document 的区别：
        - 文件哈希在调用前已计算
        - 文件数据以流的形式处理，不全部加载到内存
        """
        # 验证知识库
        await self._verify_knowledge_base(knowledge_base_id, tenant_id)

        # 文件安全校验
        validate_file(filename, file_size, mime_type)

        # 检测重复
        existing = await self.db.execute(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.knowledge_base_id == knowledge_base_id,
                Document.file_hash == file_hash,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(
                message="相同内容的文件已存在于此知识库中",
                details={"knowledge_base_id": knowledge_base_id, "file_hash": file_hash},
            )

        # 创建文档记录
        ext = os.path.splitext(filename)[1].lower()
        doc = Document(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            name=filename,
            original_filename=filename,
            file_type=ext.lstrip("."),
            mime_type=mime_type or "application/octet-stream",
            file_size=file_size,
            file_hash=file_hash,
            file_path="",
            status="draft",
            current_version=1,
            created_by=user_id,
        )
        self.db.add(doc)
        await self.db.flush()

        # 构建存储路径
        storage_key = build_storage_key(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            document_id=doc.id,
            version=1,
            file_hash=file_hash,
            extension=ext,
        )

        try:
            self.storage.upload_file_stream(
                file_stream=file_stream,
                file_size=file_size,
                storage_key=storage_key,
                content_type=mime_type,
            )
            doc.file_path = storage_key
        except StorageError:
            await self.db.rollback()
            raise

        # 创建版本记录
        version = DocumentVersion(
            tenant_id=tenant_id,
            document_id=doc.id,
            knowledge_base_id=knowledge_base_id,
            version=1,
            file_path=storage_key,
            file_size=file_size,
            file_hash=file_hash,
            is_current_version=True,
            change_summary="初始版本",
            publish_status="draft",
            created_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()

        await self._increment_kb_document_count(knowledge_base_id, tenant_id)
        return doc

    # -------------------------------------------------------------------------
    # 文档查询
    # -------------------------------------------------------------------------

    async def get_document(self, doc_id: str, tenant_id: str) -> Document:
        """获取文档详情"""
        result = await self.db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ResourceNotFoundError(resource_type="文档", resource_id=doc_id)
        return doc

    async def list_documents(
        self,
        tenant_id: str,
        pagination: PaginationParams,
        params: DocumentListParams,
    ) -> tuple[list[Document], int]:
        """分页查询文档列表"""
        query = select(Document).where(Document.tenant_id == tenant_id)

        if params.knowledge_base_id:
            query = query.where(Document.knowledge_base_id == params.knowledge_base_id)
        if params.keyword:
            query = query.where(Document.name.ilike(f"%{params.keyword}%"))
        if params.status:
            query = query.where(Document.status == params.status)
        if params.file_type:
            query = query.where(Document.file_type == params.file_type)

        # 总数
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # 分页
        query = query.offset(pagination.offset).limit(pagination.limit)
        query = query.order_by(Document.created_at.desc())
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_chunk_count(self, doc_id: str) -> int:
        """获取文档的Chunk数量"""
        result = await self.db.execute(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == doc_id,
            )
        )
        return result.scalar() or 0

    # -------------------------------------------------------------------------
    # 文档发布控制
    # -------------------------------------------------------------------------

    async def publish_document(self, doc_id: str, tenant_id: str) -> Document:
        """发布文档（使其可被成员6检索）"""
        doc = await self.get_document(doc_id, tenant_id)

        if doc.status != "pending_publish":
            raise BusinessStateError(
                message="只有待发布状态的文档可以发布",
                current_state=doc.status,
                expected_state="pending_publish",
            )

        doc.status = "published"
        doc.published_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("document_published", document_id=doc_id)
        return doc

    async def pause_document(self, doc_id: str, tenant_id: str) -> Document:
        """暂停文档（暂停后不可检索，但可以恢复）"""
        doc = await self.get_document(doc_id, tenant_id)

        if doc.status != "published":
            raise BusinessStateError(
                message="只有已发布状态的文档可以暂停",
                current_state=doc.status,
                expected_state="published",
            )

        doc.status = "paused"
        await self.db.flush()
        logger.info("document_paused", document_id=doc_id)
        return doc

    async def offline_document(self, doc_id: str, tenant_id: str) -> Document:
        """
        下线文档

        下线后立即从正式召回范围排除。成员6无法检索到该文档的Chunk。
        """
        doc = await self.get_document(doc_id, tenant_id)

        if doc.status not in ("published", "paused"):
            raise BusinessStateError(
                message="只有已发布或已暂停的文档可以下线",
                current_state=doc.status,
                expected_state="published或paused",
            )

        doc.status = "offline"
        await self.db.flush()
        logger.info("document_offlined", document_id=doc_id)
        return doc

    # -------------------------------------------------------------------------
    # 版本管理
    # -------------------------------------------------------------------------

    async def get_versions(
        self, doc_id: str, tenant_id: str
    ) -> list[DocumentVersion]:
        """获取文档的所有版本列表"""
        await self.get_document(doc_id, tenant_id)  # 确认文档存在

        result = await self.db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == doc_id,
                DocumentVersion.tenant_id == tenant_id,
            ).order_by(DocumentVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_version_detail(
        self, doc_id: str, version_id: str, tenant_id: str
    ) -> DocumentVersion:
        """获取文档特定版本的详情"""
        result = await self.db.execute(
            select(DocumentVersion).where(
                DocumentVersion.id == version_id,
                DocumentVersion.document_id == doc_id,
                DocumentVersion.tenant_id == tenant_id,
            )
        )
        ver = result.scalar_one_or_none()
        if ver is None:
            raise ResourceNotFoundError(
                resource_type="文档版本",
                resource_id=version_id,
            )
        return ver

    # -------------------------------------------------------------------------
    # 内部辅助方法
    # -------------------------------------------------------------------------

    async def _increment_kb_document_count(
        self, kb_id: str, tenant_id: str
    ) -> None:
        """增加知识库的文档计数"""
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.tenant_id == tenant_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb:
            kb.document_count = (kb.document_count or 0) + 1
            await self.db.flush()
