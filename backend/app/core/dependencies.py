"""
依赖注入模块
提供 FastAPI 依赖注入函数
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AccessContext, verify_token
from app.core.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer 安全方案
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    """
    获取当前用户 ID
    如果未认证返回 None
    """
    if credentials is None:
        return None

    payload = verify_token(credentials.credentials, "access")
    if payload is None:
        return None

    return payload.get("sub")


async def get_required_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """
    获取当前用户 ID（必须认证）
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials, "access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_access_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessContext:
    """
    获取访问上下文
    包含用户信息、角色、权限和数据范围。
    启用 USE_MEMBER4_PERMISSION 时，用 PermissionService 补齐数据权限字段。
    """
    from app.retrieval.member4_bridge import safe_enrich_access

    # 如果没有认证，返回空上下文
    if credentials is None:
        return AccessContext(
            user_id="anonymous",
            tenant_id="",
            roles=[],
            permissions=[],
            data_scopes={},
        )

    # 验证令牌
    payload = verify_token(credentials.credentials, "access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 从令牌中提取访问上下文
    access = AccessContext(
        user_id=payload.get("sub", ""),
        tenant_id=payload.get("tenant_id", ""),
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        data_scopes=payload.get("data_scopes", {}),
    )
    return await safe_enrich_access(db, access)


async def get_required_access_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessContext:
    """
    获取访问上下文（必须认证）
    """
    from app.retrieval.member4_bridge import safe_enrich_access

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials, "access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access = AccessContext(
        user_id=payload.get("sub", ""),
        tenant_id=payload.get("tenant_id", ""),
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        data_scopes=payload.get("data_scopes", {}),
    )
    return await safe_enrich_access(db, access)


def require_permission(permission: str):
    """
    权限检查依赖
    用法: @router.get("/", dependencies=[Depends(require_permission("document:read"))])
    """

    async def check_permission(
        access_context: Annotated[AccessContext, Depends(get_access_context)],
    ) -> AccessContext:
        if permission not in access_context.permissions and "*" not in access_context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要权限: {permission}",
            )
        return access_context

    return check_permission


def require_role(role: str):
    """
    角色检查依赖
    """

    async def check_role(
        access_context: Annotated[AccessContext, Depends(get_access_context)],
    ) -> AccessContext:
        if role not in access_context.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {role}",
            )
        return access_context

    return check_role


# 类型别名
CurrentUser = Annotated[str | None, Depends(get_current_user_id)]
RequiredUser = Annotated[str, Depends(get_required_user_id)]
CurrentAccess = Annotated[AccessContext, Depends(get_access_context)]
RequiredAccess = Annotated[AccessContext, Depends(get_required_access_context)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
