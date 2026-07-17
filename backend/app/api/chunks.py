"""
Chunk 路由

提供文档切分块查询 API。

成员5主责：Chunk 相关全部端点
"""
from sqlalchemy import func, select
from fastapi import APIRouter

from app.core.dependencies import DBSession
from app.core.exceptions import ResourceNotFoundError
from app.core.responses import success_response, paginated_response
from app.models.document import DocumentChunk
from app.schemas.document import ChunkDetailResponse, ChunkResponse, ChunkListParams

router = APIRouter()
chunks_router = router


@router.get("", summary="Chunk列表")
async def list_chunks(
    db: DBSession,
    document_id: str | None = None,
    document_version_id: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """获取Chunk列表（分页+搜索+筛选）"""
    query = select(DocumentChunk)

    if document_id:
        query = query.where(DocumentChunk.document_id == document_id)
    if document_version_id:
        query = query.where(DocumentChunk.document_version_id == document_version_id)
    if keyword:
        query = query.where(DocumentChunk.clean_text.ilike(f"%{keyword}%"))
    if status:
        query = query.where(DocumentChunk.status == status)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(DocumentChunk.chunk_no.asc())
    result = await db.execute(query)
    items = list(result.scalars().all())

    return paginated_response(
        items=[ChunkResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="查询成功",
    )


@router.get("/{chunk_id}", summary="Chunk详情")
async def get_chunk(
    chunk_id: str,
    db: DBSession,
):
    """获取Chunk详细信息（含原始文本和元数据）"""
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    )
    chunk = result.scalar_one_or_none()
    if chunk is None:
        raise ResourceNotFoundError(resource_type="Chunk", resource_id=chunk_id)

    return success_response(
        data=ChunkDetailResponse.model_validate(chunk),
        message="查询成功",
    )
