"""
标准问答路由（成员7）
提供标准问答的完整生命周期管理、审核发布、候选问答、匹配等接口
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentAccess, DBSession, RequiredAccess, require_permission
from app.core.exceptions import BusinessStateError, ResourceNotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.responses import error_response, paginated_response, success_response
from app.models.qa import QAStatus, ReviewAction
from app.schemas.common import PaginationParams
from app.schemas.qa import (
    CandidateQABatchReviewRequest,
    CandidateQAGenerateRequest,
    CandidateQAQueryParams,
    CandidateQAReviewRequest,
    CandidateQAResponse,
    QAMatchRequest,
    QAMatchResponse,
    QAMatchResult,
    QAQualityCheckResponse,
    QAQualityCheckSummary,
    QAQueryParams,
    QAReviewRecordResponse,
    QAReviewSubmitRequest,
    ReviewQueryParams,
    StandardQACreate,
    StandardQADetailResponse,
    StandardQADisableRequest,
    StandardQAPublishRequest,
    StandardQAResponse,
    StandardQAUpdate,
)
from app.services.qa_matching_service import qa_matching_service
from app.services.qa_quality_service import qa_quality_check_service
from app.services.qa_service import qa_service

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# 标准问答 CRUD
# ============================================================================

@router.post("/standard", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_standard_qa(
    data: StandardQACreate,
    db: DBSession,
    access: RequiredAccess,
):
    """创建标准问答（草稿状态）"""
    qa = await qa_service.create_qa(
        db=db,
        data=data.model_dump(),
        user_id=access.user_id,
        tenant_id=access.tenant_id,
    )
    return success_response(
        data={"id": qa.id, "status": qa.status},
        message="标准问答创建成功",
    )


@router.get("/standard")
async def list_standard_qas(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, description="搜索关键词"),
    status: str | None = Query(default=None, description="状态筛选"),
    category: str | None = Query(default=None, description="分类筛选"),
    knowledge_base_id: str | None = Query(default=None, description="知识库 ID 筛选"),
    is_machine_generated: bool | None = Query(default=None, description="是否机器生成"),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
):
    """查询标准问答列表"""
    items, total = await qa_service.list_qas(
        db=db,
        tenant_id=access.tenant_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        category=category,
        knowledge_base_id=knowledge_base_id,
        is_machine_generated=is_machine_generated,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_response(
        items=[StandardQAResponse.model_validate(item).model_dump() for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/standard/{qa_id}")
async def get_standard_qa(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """获取标准问答详情"""
    qa = await qa_service.get_qa_or_raise(db, qa_id, load_relations=True)
    return success_response(
        data=StandardQADetailResponse.model_validate(qa).model_dump(),
    )


@router.put("/standard/{qa_id}")
async def update_standard_qa(
    qa_id: str,
    data: StandardQAUpdate,
    db: DBSession,
    access: RequiredAccess,
):
    """更新标准问答"""
    qa = await qa_service.update_qa(
        db=db,
        qa_id=qa_id,
        data=data.model_dump(exclude_none=True),
        user_id=access.user_id,
    )
    return success_response(
        data=StandardQAResponse.model_validate(qa).model_dump(),
        message="标准问答更新成功",
    )


# ============================================================================
# 审核流程
# ============================================================================

@router.post("/standard/{qa_id}/submit-review")
async def submit_for_review(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """提交审核"""
    qa = await qa_service.submit_for_review(db, qa_id, access.user_id)
    return success_response(
        data={"id": qa.id, "status": qa.status},
        message="已提交审核",
    )


@router.post("/reviews")
async def submit_review(
    data: QAReviewSubmitRequest,
    db: DBSession,
    access: RequiredAccess,
):
    """提交审核结果"""
    action = data.action
    qa_id = data.qa_id

    if action == ReviewAction.APPROVE:
        qa = await qa_service.approve_review(
            db, qa_id, access.user_id, data.comment, data.review_details
        )
    elif action == ReviewAction.REJECT:
        qa = await qa_service.reject_review(
            db, qa_id, access.user_id, data.comment, data.review_details
        )
    elif action == ReviewAction.RETURN_FOR_MODIFICATION:
        qa = await qa_service.return_for_modification(
            db, qa_id, access.user_id, data.comment
        )
    elif action == ReviewAction.PUBLISH:
        qa = await qa_service.publish_qa(db, qa_id, access.user_id)
    elif action == ReviewAction.DISABLE:
        qa = await qa_service.disable_qa(
            db, qa_id, access.user_id, data.comment or "手动停用"
        )
    elif action == ReviewAction.MARK_DUPLICATE:
        duplicate_of_id = (data.review_details or {}).get("duplicate_of_id", "")
        if not duplicate_of_id:
            raise ValidationError("标记重复时需要指定目标问答 ID")
        qa = await qa_service.mark_as_duplicate(
            db, qa_id, duplicate_of_id, access.user_id
        )
    elif action == ReviewAction.MARK_SOURCE_ISSUE:
        qa = await qa_service.disable_qa(
            db, qa_id, access.user_id, data.comment or "来源文档问题"
        )
    else:
        raise ValidationError(f"不支持的审核动作: {action}")

    return success_response(
        data={"id": qa.id, "status": qa.status},
        message=f"审核操作 '{action}' 执行成功",
    )


@router.get("/reviews")
async def list_review_records(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    qa_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    reviewer_id: str | None = Query(default=None),
    sort_by: str = Query(default="review_time"),
    sort_order: str = Query(default="desc"),
):
    """查询审核记录"""
    items, total = await qa_service.list_review_records(
        db=db,
        tenant_id=access.tenant_id,
        page=page,
        page_size=page_size,
        qa_id=qa_id,
        action=action,
        reviewer_id=reviewer_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_response(
        items=[QAReviewRecordResponse.model_validate(item).model_dump() for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# 发布与停用
# ============================================================================

@router.post("/standard/{qa_id}/publish")
async def publish_standard_qa(
    qa_id: str,
    data: StandardQAPublishRequest | None = None,
    db: DBSession = Depends(),
    access: RequiredAccess = Depends(),
):
    """发布标准问答"""
    qa = await qa_service.publish_qa(
        db=db,
        qa_id=qa_id,
        user_id=access.user_id,
        effective_start=data.effective_start if data else None,
        effective_end=data.effective_end if data else None,
    )
    return success_response(
        data={"id": qa.id, "status": qa.status, "published_at": qa.published_at.isoformat() if qa.published_at else None},
        message="标准问答已发布",
    )


@router.post("/standard/{qa_id}/disable")
async def disable_standard_qa(
    qa_id: str,
    data: StandardQADisableRequest,
    db: DBSession,
    access: RequiredAccess,
):
    """停用标准问答"""
    qa = await qa_service.disable_qa(
        db=db,
        qa_id=qa_id,
        user_id=access.user_id,
        reason=data.reason,
    )
    return success_response(
        data={"id": qa.id, "status": qa.status},
        message="标准问答已停用",
    )


# ============================================================================
# 候选问答
# ============================================================================

@router.post("/candidates/generate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_candidate_generation(
    data: CandidateQAGenerateRequest,
    background_tasks: BackgroundTasks,
    access: RequiredAccess,
):
    """触发候选问答生成任务（异步）"""
    from app.tasks.qa_tasks import generate_candidate_qas

    # 使用 BackgroundTasks 异步执行
    background_tasks.add_task(
        generate_candidate_qas,
        knowledge_base_id=data.knowledge_base_id,
        document_ids=data.document_ids,
        chunk_ids=data.chunk_ids,
        max_candidates=data.max_candidates,
        model=data.model,
        prompt_version=data.prompt_version,
        user_id=access.user_id,
        tenant_id=access.tenant_id,
    )

    return success_response(
        data={
            "knowledge_base_id": data.knowledge_base_id,
            "status": "processing",
        },
        message="候选问答生成任务已触发",
    )


@router.get("/candidates")
async def list_candidates(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    knowledge_base_id: str | None = Query(default=None),
    source: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
):
    """查询候选问答列表"""
    items, total = await qa_service.list_candidates(
        db=db,
        tenant_id=access.tenant_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        knowledge_base_id=knowledge_base_id,
        source=source,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_response(
        items=[CandidateQAResponse.model_validate(item).model_dump() for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/candidates/{candidate_id}/review")
async def review_candidate(
    candidate_id: str,
    data: CandidateQAReviewRequest,
    db: DBSession,
    access: RequiredAccess,
):
    """审核候选问答"""
    action = data.action

    if action == "approve":
        candidate = await qa_service.approve_candidate(
            db, candidate_id, access.user_id, data.comment
        )
        message = "候选问答审核通过"
    elif action == "reject":
        candidate = await qa_service.reject_candidate(
            db, candidate_id, access.user_id, data.comment
        )
        message = "候选问答已驳回"
    elif action == "mark_duplicate":
        candidate = await qa_service.reject_candidate(
            db, candidate_id, access.user_id,
            f"标记为重复: {data.duplicate_of_standard_id or ''}"
        )
        message = "候选问答已标记为重复"
    else:
        raise ValidationError(f"不支持的审核动作: {action}")

    return success_response(
        data={"id": candidate.id, "status": candidate.status},
        message=message,
    )


@router.post("/candidates/{candidate_id}/convert")
async def convert_candidate_to_standard(
    candidate_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """将候选问答转为标准问答"""
    qa = await qa_service.convert_candidate_to_standard(
        db, candidate_id, access.user_id
    )
    return success_response(
        data={"id": qa.id, "status": qa.status, "question": qa.question},
        message="候选问答已转为标准问答",
    )


# ============================================================================
# 标准问答匹配（供成员6调用）
# ============================================================================

@router.post("/match")
async def match_standard_qa(
    data: QAMatchRequest,
    db: DBSession,
):
    """
    标准问答匹配接口
    供成员6的正式问答链路调用，在执行 RAG 检索前先匹配标准问答
    """
    result = await qa_matching_service.match(
        db=db,
        query=data.query,
        keywords=data.keywords,
        entities=data.entities,
        intent=data.intent,
        access_context=data.access_context,
        knowledge_base_ids=data.knowledge_base_ids,
        top_k=data.top_k,
        threshold=data.threshold,
    )

    return success_response(data=result)


# ============================================================================
# 质量检查
# ============================================================================

@router.post("/standard/{qa_id}/quality-check")
async def run_quality_check(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
    background_tasks: BackgroundTasks,
):
    """触发质量检查"""
    from app.tasks.qa_tasks import run_quality_checks

    background_tasks.add_task(run_quality_checks, qa_id=qa_id)

    return success_response(
        data={"qa_id": qa_id, "status": "processing"},
        message="质量检查任务已触发",
    )


@router.get("/standard/{qa_id}/quality-check")
async def get_quality_check_result(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """获取质量检查结果"""
    summary = await qa_quality_check_service.get_check_summary(db, qa_id)
    return success_response(data=summary)


# ============================================================================
# 文档版本联动（内部接口）
# ============================================================================

@router.post("/internal/document-change")
async def handle_document_change(
    event_type: str = Query(..., description="事件类型"),
    document_id: str = Query(..., description="文档 ID"),
    new_version: int = Query(default=1, description="新版本号"),
    db: DBSession = Depends(),
):
    """
    处理文档版本变更（内部接口）
    由 Outbox 事件消费者或文档服务调用
    """
    from app.services.outbox_consumer import outbox_event_consumer

    result = await outbox_event_consumer.handle_single_event(
        db=db,
        event_type=event_type,
        document_id=document_id,
        new_version=new_version,
    )
    return success_response(data=result, message="文档变更已处理")


# ============================================================================
# 状态流转查询
# ============================================================================

@router.get("/standard/{qa_id}/allowed-transitions")
async def get_allowed_transitions(
    qa_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """获取当前状态允许的流转目标"""
    qa = await qa_service.get_qa_or_raise(db, qa_id)
    allowed = qa_service.get_allowed_transitions(qa.status)
    return success_response(
        data={
            "qa_id": qa_id,
            "current_status": qa.status,
            "allowed_transitions": allowed,
        }
    )