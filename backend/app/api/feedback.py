"""
<<<<<<< HEAD
反馈与运营路由（成员7）
提供用户反馈提交、未命中问题、高频问题、低质量答案、知识缺口等运营接口
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentAccess, DBSession, RequiredAccess
from app.core.logging import get_logger
from app.core.responses import paginated_response, success_response
from app.models.qa import Message, StandardQA, UserFeedback

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# 用户反馈
# ============================================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    data: dict,
    db: DBSession,
    access: RequiredAccess,
):
    """
    提交用户反馈
    支持：点赞（positive）、点踩（negative）、纠错（correction）
    """
    message_id = data.get("message_id", "")
    feedback_type = data.get("feedback_type", data.get("feedback", ""))
    comment = data.get("comment")
    correction_text = data.get("correction_text")
    score = data.get("score")
    qa_id = data.get("qa_id")

    if feedback_type not in ("positive", "negative", "correction"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="反馈类型必须是 positive、negative 或 correction",
        )

    feedback = UserFeedback(
        message_id=message_id,
        qa_id=qa_id,
        feedback_type=feedback_type,
        comment=comment,
        correction_text=correction_text,
        score=score,
        is_resolved=False,
        tenant_id=access.tenant_id,
        created_by=access.user_id,
    )
    db.add(feedback)

    # 更新标准问答的反馈计数
    if qa_id and feedback_type in ("positive", "negative"):
        stmt = select(StandardQA).where(
            StandardQA.id == qa_id,
            StandardQA.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        qa = result.scalar_one_or_none()
        if qa:
            if feedback_type == "positive":
                qa.positive_feedback_count = (qa.positive_feedback_count or 0) + 1
            else:
                qa.negative_feedback_count = (qa.negative_feedback_count or 0) + 1

    await db.flush()

    logger.info(
        "feedback_submitted",
        feedback_type=feedback_type,
        message_id=message_id,
        qa_id=qa_id,
    )

    return success_response(
        data={"id": feedback.id, "feedback_type": feedback_type},
        message="反馈提交成功",
    )


@router.get("/")
async def list_feedbacks(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    feedback_type: str | None = Query(default=None, description="反馈类型筛选"),
    is_resolved: bool | None = Query(default=None, description="是否已处理"),
    qa_id: str | None = Query(default=None, description="标准问答 ID 筛选"),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
):
    """查询反馈列表"""
    conditions = [
        UserFeedback.tenant_id == access.tenant_id,
        UserFeedback.deleted_at.is_(None),
    ]

    if feedback_type:
        conditions.append(UserFeedback.feedback_type == feedback_type)
    if is_resolved is not None:
        conditions.append(UserFeedback.is_resolved == is_resolved)
    if qa_id:
        conditions.append(UserFeedback.qa_id == qa_id)

    count_stmt = select(func.count()).select_from(UserFeedback).where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar() or 0

    sort_col = getattr(UserFeedback, sort_by, UserFeedback.created_at)
    order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

    stmt = (
        select(UserFeedback)
        .where(and_(*conditions))
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return paginated_response(
        items=[
            {
                "id": item.id,
                "message_id": item.message_id,
                "qa_id": item.qa_id,
                "feedback_type": item.feedback_type,
                "comment": item.comment,
                "correction_text": item.correction_text,
                "score": item.score,
                "is_resolved": item.is_resolved,
                "resolved_by": item.resolved_by,
                "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "created_by": item.created_by,
            }
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: str,
    db: DBSession,
    access: RequiredAccess,
):
    """标记反馈为已处理"""
    stmt = select(UserFeedback).where(
        UserFeedback.id == feedback_id,
        UserFeedback.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    feedback = result.scalar_one_or_none()
    if feedback is None:
        raise HTTPException(status_code=404, detail="反馈不存在")

    feedback.is_resolved = True
    feedback.resolved_by = access.user_id
    feedback.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    return success_response(data={"id": feedback_id}, message="反馈已处理")


# ============================================================================
# 知识运营分析
# ============================================================================

@router.get("/operations/unanswered")
async def get_unanswered_questions(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=30, description="统计天数"),
    knowledge_base_id: str | None = Query(default=None, description="知识库 ID 筛选"),
):
    """
    查询未命中问题
    识别用户提问但未命中标准问答且 RAG 拒答或低质量回答的情况
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    conditions = [
        Message.tenant_id == access.tenant_id,
        Message.role == "user",
        Message.created_at >= since,
        Message.deleted_at.is_(None),
        # 未匹配到标准问答
        Message.matched_qa_id.is_(None),
    ]

    if knowledge_base_id:
        # 通过 metadata 中的 knowledge_base_id 过滤
        conditions.append(
            Message.metadata.op("->>")("knowledge_base_id") == knowledge_base_id
        )

    count_stmt = select(func.count()).select_from(Message).where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Message)
        .where(and_(*conditions))
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return paginated_response(
        items=[
            {
                "id": item.id,
                "content": item.content,
                "intent": item.intent,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "user_id": item.created_by,
            }
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/operations/high-frequency")
async def get_high_frequency_questions(
    db: DBSession,
    access: RequiredAccess,
    days: int = Query(default=7, description="统计天数"),
    top_n: int = Query(default=20, ge=1, le=100, description="返回数量"),
    knowledge_base_id: str | None = Query(default=None),
):
    """
    查询高频问题
    按时间窗口统计高频查询
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 统计用户消息中的高频问题
    conditions = [
        Message.tenant_id == access.tenant_id,
        Message.role == "user",
        Message.created_at >= since,
        Message.deleted_at.is_(None),
    ]

    if knowledge_base_id:
        conditions.append(
            Message.metadata.op("->>")("knowledge_base_id") == knowledge_base_id
        )

    stmt = (
        select(
            Message.content,
            func.count(Message.id).label("count"),
            func.count(func.distinct(Message.created_by)).label("unique_users"),
        )
        .where(and_(*conditions))
        .group_by(Message.content)
        .order_by(text("count DESC"))
        .limit(top_n)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return success_response(
        data={
            "period_days": days,
            "since": since.isoformat(),
            "questions": [
                {
                    "content": row.content,
                    "count": row.count,
                    "unique_users": row.unique_users,
                }
                for row in rows
            ],
        }
    )


@router.get("/operations/low-quality")
async def get_low_quality_answers(
    db: DBSession,
    access: RequiredAccess,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=30, description="统计天数"),
    min_negative_feedback: int = Query(default=3, description="最少负反馈数量"),
):
    """
    查询低质量答案
    基于用户点踩和引用质量识别
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 查找负反馈较多的标准问答
    stmt = (
        select(
            StandardQA,
            func.count(UserFeedback.id).label("negative_count"),
        )
        .join(UserFeedback, UserFeedback.qa_id == StandardQA.id)
        .where(
            and_(
                StandardQA.tenant_id == access.tenant_id,
                StandardQA.deleted_at.is_(None),
                UserFeedback.feedback_type == "negative",
                UserFeedback.created_at >= since,
            )
        )
        .group_by(StandardQA.id)
        .having(func.count(UserFeedback.id) >= min_negative_feedback)
        .order_by(text("negative_count DESC"))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # 统计总数
    count_stmt = (
        select(func.count(func.distinct(StandardQA.id)))
        .select_from(StandardQA)
        .join(UserFeedback, UserFeedback.qa_id == StandardQA.id)
        .where(
            and_(
                StandardQA.tenant_id == access.tenant_id,
                StandardQA.deleted_at.is_(None),
                UserFeedback.feedback_type == "negative",
                UserFeedback.created_at >= since,
            )
        )
        .having(func.count(UserFeedback.id) >= min_negative_feedback)
    )
    # 子查询方式获取总数
    total = len(rows)  # 简化处理

    return paginated_response(
        items=[
            {
                "qa_id": row.StandardQA.id,
                "question": row.StandardQA.question[:100],
                "status": row.StandardQA.status,
                "negative_feedback_count": row.negative_count,
                "total_feedback_count": (
                    row.StandardQA.positive_feedback_count
                    + row.StandardQA.negative_feedback_count
                ),
            }
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/operations/knowledge-gaps")
async def get_knowledge_gaps(
    db: DBSession,
    access: RequiredAccess,
    days: int = Query(default=30, description="统计天数"),
    top_n: int = Query(default=20, ge=1, le=100),
):
    """
    查询知识缺口任务
    来源包括：高频拒答、多次改写仍未命中、用户集中点踩、
    同一问题冲突答案、某部门高频询问但无正式文档
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    gaps: list[dict[str, Any]] = []

    # 1. 高频未命中问题
    unmet_stmt = (
        select(
            Message.content,
            func.count(Message.id).label("count"),
        )
        .where(
            and_(
                Message.tenant_id == access.tenant_id,
                Message.role == "user",
                Message.created_at >= since,
                Message.matched_qa_id.is_(None),
                Message.deleted_at.is_(None),
            )
        )
        .group_by(Message.content)
        .order_by(text("count DESC"))
        .limit(top_n)
    )
    unmet_result = await db.execute(unmet_stmt)
    for row in unmet_result.all():
        if row.count >= 3:  # 至少3次未命中
            gaps.append({
                "type": "unanswered",
                "content": row.content[:200],
                "frequency": row.count,
                "source": "高频拒答/未命中",
            })

    # 2. 高负反馈问答
    negative_stmt = (
        select(
            StandardQA,
            func.count(UserFeedback.id).label("neg_count"),
        )
        .join(UserFeedback, UserFeedback.qa_id == StandardQA.id)
        .where(
            and_(
                StandardQA.tenant_id == access.tenant_id,
                StandardQA.deleted_at.is_(None),
                UserFeedback.feedback_type == "negative",
                UserFeedback.created_at >= since,
            )
        )
        .group_by(StandardQA.id)
        .having(func.count(UserFeedback.id) >= 5)
        .order_by(text("neg_count DESC"))
        .limit(top_n)
    )
    neg_result = await db.execute(negative_stmt)
    for row in neg_result.all():
        gaps.append({
            "type": "low_quality",
            "qa_id": row.StandardQA.id,
            "content": row.StandardQA.question[:200],
            "negative_count": row.neg_count,
            "source": "用户集中点踩",
        })

    # 按关注度排序
    gaps.sort(key=lambda x: x.get("frequency", x.get("negative_count", 0)), reverse=True)

    return success_response(
        data={
            "period_days": days,
            "since": since.isoformat(),
            "total_gaps": len(gaps),
            "gaps": gaps[:top_n],
        }
    )
=======
反馈路由占位
由成员7实现
"""
from fastapi import APIRouter

router = APIRouter()

# TODO: 由成员7实现
# - POST / - 提交反馈
# - GET /message/{message_id} - 获取消息的反馈
>>>>>>> 8de89ee904f686dbe7d52e3b35cdc79ef917eeb2
