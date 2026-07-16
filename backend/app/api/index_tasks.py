"""
索引任务路由

提供索引任务列表、详情、重试、重建和一致性检查 API。

成员5主责: 索引任务管理全部端点
"""
from fastapi import APIRouter

from app.core.database import get_db
from app.core.dependencies import DBSession
from app.core.responses import success_response, paginated_response
from app.schemas.common import PaginationParams
from app.schemas.document import (
    IndexTaskResponse,
    IndexTaskListParams,
    ConsistencyCheckRequest,
)
from app.services.indexing import IndexingService

router = APIRouter()


def get_index_service(db: DBSession) -> IndexingService:
    """依赖注入：获取索引服务实例"""
    return IndexingService(db)


@router.get("", summary="索引任务列表")
async def list_index_tasks(
    db: DBSession,
    document_id: str | None = None,
    status: str | None = None,
    task_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """获取索引任务列表（分页+状态筛选）"""
    from app.models.document import IndexTask
    from sqlalchemy import func, select

    query = select(IndexTask)

    if document_id:
        query = query.where(IndexTask.document_id == document_id)
    if status:
        query = query.where(IndexTask.status == status)
    if task_type:
        query = query.where(IndexTask.task_type == task_type)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(IndexTask.created_at.desc())
    result = await db.execute(query)
    items = list(result.scalars().all())

    return paginated_response(
        items=[IndexTaskResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="查询成功",
    )


@router.get("/{task_id}", summary="索引任务详情")
async def get_index_task(task_id: str, db: DBSession):
    """获取单个索引任务的详细信息"""
    from app.models.document import IndexTask
    from app.core.exceptions import ResourceNotFoundError
    from sqlalchemy import select

    result = await db.execute(select(IndexTask).where(IndexTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise ResourceNotFoundError(resource_type="索引任务", resource_id=task_id)

    return success_response(
        data=IndexTaskResponse.model_validate(task),
        message="查询成功",
    )


@router.post("/{task_id}/retry", summary="重试失败任务")
async def retry_index_task(task_id: str, db: DBSession):
    """重试失败的索引任务"""
    from app.models.document import IndexTask
    from app.core.exceptions import BusinessStateError
    from sqlalchemy import select

    result = await db.execute(select(IndexTask).where(IndexTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource_type="索引任务", resource_id=task_id)

    if task.status != "failed":
        raise BusinessStateError(
            message="只有失败的索引任务可以重试",
            current_state=task.status,
            expected_state="failed",
        )

    task.status = "pending"
    task.retry_count = 0
    task.error_message = None
    await db.flush()

    return success_response(
        data=IndexTaskResponse.model_validate(task),
        message="索引任务已重置为待处理",
    )


@router.post("/rebuild", summary="重建索引")
async def rebuild_index(
    db: DBSession,
    knowledge_base_id: str | None = None,
    document_id: str | None = None,
):
    """重建指定范围的索引"""
    service = IndexingService(db)

    # 创建重建任务
    task = await service.create_index_task(
        tenant_id="default",
        document_id=document_id or "all",
        document_version_id="all",
        task_type="rebuild",
        target="both",
    )

    return success_response(
        data=IndexTaskResponse.model_validate(task),
        message="重建索引任务已创建",
    )


@router.post("/consistency-check", summary="一致性检查")
async def consistency_check(
    db: DBSession,
    body: ConsistencyCheckRequest | None = None,
):
    """
    检查OpenSearch和pgvector索引与PostgreSQL的一致性

    可选自动修复不一致的索引。
    """
    kb_id = body.knowledge_base_id if body else None
    auto_fix = body.auto_fix if body else False

    service = IndexingService(db)
    result = await service.consistency_check(
        knowledge_base_id=kb_id,
        auto_fix=auto_fix,
    )

    return success_response(
        data=result,
        message=f"一致性检查完成：总{result['total_chunks']}个Chunk，"
                f"OpenSearch缺失{result['missing_opensearch']}个，"
                f"pgvector缺失{result['missing_pgvector']}个",
    )
