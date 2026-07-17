"""
文档路由

提供文档上传、查询、发布控制、版本管理 API。

成员5主责：文档相关全部端点
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, DBSession
from app.core.responses import success_response, paginated_response
from app.schemas.common import PaginationParams
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListParams,
    DocumentResponse,
    DocumentUploadResponse,
    DocumentVersionResponse,
)
from app.services.document import DocumentService

router = APIRouter()
documents_router = router


def get_doc_service(db: DBSession) -> DocumentService:
    """依赖注入：获取文档服务实例"""
    return DocumentService(db)


# =============================================================================
# 文档上传
# =============================================================================

@router.post("/upload", summary="单文件上传")
async def upload_document(
    file: UploadFile,
    knowledge_base_id: str = Form(..., description="目标知识库ID"),
    user_id: CurrentUser = "system",
    db: AsyncSession = Depends(get_db),
):
    """
    上传单个文档到指定知识库

    流程:
    1. 校验文件格式和大小
    2. 计算SHA-256哈希
    3. 检测重复文件
    4. 上传到MinIO
    5. 创建文档记录和版本记录
    """
    service = DocumentService(db)
    file_data = await file.read()

    doc = await service.upload_document(
        tenant_id="default",
        user_id=user_id or "system",
        knowledge_base_id=knowledge_base_id,
        filename=file.filename or "unknown",
        file_data=file_data,
        mime_type=file.content_type,
    )

    return success_response(
        data=DocumentUploadResponse(
            document_id=doc.id,
            name=doc.name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            file_hash=doc.file_hash,
            status=doc.status,
        ),
        message="文档上传成功",
    )


@router.post("/batch-upload", summary="批量上传")
async def batch_upload_documents(
    files: list[UploadFile],
    knowledge_base_id: str = Form(..., description="目标知识库ID"),
    user_id: CurrentUser = "system",
    db: AsyncSession = Depends(get_db),
):
    """
    批量上传文档到指定知识库

    返回每个文件的上传结果（成功或失败及原因）。
    """
    service = DocumentService(db)
    results = []
    success_count = 0
    failed_count = 0

    for file in files:
        try:
            file_data = await file.read()
            doc = await service.upload_document(
                tenant_id="default",
                user_id=user_id or "system",
                knowledge_base_id=knowledge_base_id,
                filename=file.filename or "unknown",
                file_data=file_data,
                mime_type=file.content_type,
            )
            results.append({
                "filename": file.filename,
                "success": True,
                "document_id": doc.id,
                "file_hash": doc.file_hash,
            })
            success_count += 1
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e),
            })
            failed_count += 1

    return success_response(
        data={
            "total": len(files),
            "success": success_count,
            "failed": failed_count,
            "results": results,
        },
        message=f"批量上传完成: 成功{success_count}个, 失败{failed_count}个",
    )


# =============================================================================
# 文档查询
# =============================================================================

@router.get("", summary="文档列表")
async def list_documents(
    db: DBSession,
    knowledge_base_id: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    file_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """获取文档列表（分页+搜索+状态筛选+文件类型筛选）"""
    service = DocumentService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    params = DocumentListParams(
        knowledge_base_id=knowledge_base_id,
        keyword=keyword,
        status=status,
        file_type=file_type,
    )
    items, total = await service.list_documents("default", pagination, params)

    return paginated_response(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="查询成功",
    )


@router.get("/{doc_id}", summary="文档详情")
async def get_document(
    doc_id: str,
    db: DBSession,
):
    """获取文档详情（含处理进度和Chunk数量）"""
    service = DocumentService(db)
    doc = await service.get_document(doc_id, tenant_id="default")
    chunk_count = await service.get_chunk_count(doc_id)

    detail = DocumentDetailResponse.model_validate(doc)
    detail.chunk_count = chunk_count
    return success_response(data=detail, message="查询成功")


# =============================================================================
# 文档发布控制
# =============================================================================

@router.patch("/{doc_id}/publish", summary="发布文档")
async def publish_document(
    doc_id: str,
    db: DBSession,
):
    """发布文档，使其可被检索"""
    service = DocumentService(db)
    doc = await service.publish_document(doc_id, tenant_id="default")
    return success_response(
        data=DocumentResponse.model_validate(doc),
        message="文档已发布",
    )


@router.patch("/{doc_id}/pause", summary="暂停文档")
async def pause_document(
    doc_id: str,
    db: DBSession,
):
    """暂停文档，暂停后不可检索"""
    service = DocumentService(db)
    doc = await service.pause_document(doc_id, tenant_id="default")
    return success_response(
        data=DocumentResponse.model_validate(doc),
        message="文档已暂停",
    )


@router.patch("/{doc_id}/offline", summary="下线文档")
async def offline_document(
    doc_id: str,
    db: DBSession,
):
    """下线文档，立即从正式召回范围排除"""
    service = DocumentService(db)
    doc = await service.offline_document(doc_id, tenant_id="default")
    return success_response(
        data=DocumentResponse.model_validate(doc),
        message="文档已下线",
    )


# =============================================================================
# 版本管理
# =============================================================================

@router.get("/{doc_id}/versions", summary="文档版本列表")
async def list_document_versions(
    doc_id: str,
    db: DBSession,
):
    """获取文档的所有版本列表"""
    service = DocumentService(db)
    versions = await service.get_versions(doc_id, tenant_id="default")
    return success_response(
        data=[DocumentVersionResponse.model_validate(v) for v in versions],
        message="查询成功",
    )


@router.get("/{doc_id}/versions/{version_id}", summary="版本详情")
async def get_document_version_detail(
    doc_id: str,
    version_id: str,
    db: DBSession,
):
    """获取文档特定版本的详细信息"""
    service = DocumentService(db)
    version = await service.get_version_detail(doc_id, version_id, tenant_id="default")
    return success_response(
        data=DocumentVersionResponse.model_validate(version),
        message="查询成功",
    )
