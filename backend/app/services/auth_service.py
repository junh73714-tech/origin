"""
成员4：认证服务
实现登录、刷新、退出、密码重置、登录限制等功能
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError, ResourceNotFoundError
from app.core.logging import get_logger
from app.core.security import (
    AccessContext,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.auth import Session
from app.models.identity import LoginLog
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, TokenResponse, UserResponse

logger = get_logger(__name__)

LOGIN_FAILURE_THRESHOLD = 5
LOGIN_LOCKOUT_DURATION_MINUTES = 15


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """根据用户名或邮箱获取用户"""
    result = await db.execute(
        select(User).filter(
            and_(
                User.is_active.is_(True),
                (User.username == username) | (User.email == username),
                User.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """根据ID获取用户"""
    result = await db.execute(
        select(User).filter(
            and_(
                User.id == user_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_recent_login_attempts(
    db: AsyncSession, username: str, ip_address: str | None = None
) -> list[LoginLog]:
    """获取最近的登录尝试记录"""
    time_window = datetime.now(timezone.utc) - timedelta(minutes=LOGIN_LOCKOUT_DURATION_MINUTES)
    result = await db.execute(
        select(LoginLog)
        .filter(
            and_(
                LoginLog.username == username,
                LoginLog.login_time >= time_window,
                LoginLog.success.is_(False),
            )
        )
        .order_by(LoginLog.login_time.desc())
    )
    return result.scalars().all()


async def check_login_lockout(db: AsyncSession, username: str) -> bool:
    """检查是否被锁定"""
    attempts = await get_recent_login_attempts(db, username)
    if len(attempts) >= LOGIN_FAILURE_THRESHOLD:
        logger.warning("login_locked", username=username, attempts=len(attempts))
        return True
    return False


async def create_login_log(
    db: AsyncSession,
    username: str,
    success: bool,
    user_id: str | None = None,
    failure_reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    session_id: str | None = None,
) -> None:
    """创建登录日志"""
    login_log = LoginLog(
        id=f"log_{uuid.uuid4().hex[:16]}",
        tenant_id="default",
        user_id=user_id,
        username=username,
        success=success,
        failure_reason=failure_reason,
        ip_address=ip_address,
        user_agent=user_agent,
        login_time=datetime.now(timezone.utc),
        session_id=session_id,
    )
    db.add(login_log)
    await db.flush()


async def create_user_session(
    db: AsyncSession,
    user: User,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Session:
    """创建用户会话"""
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.security.refresh_token_expire_days)
    session = Session(
        id=f"sess_{uuid.uuid4().hex[:16]}",
        tenant_id=user.tenant_id,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
        created_by=user.id,
    )
    db.add(session)
    await db.flush()
    return session


async def get_session_by_refresh_token(db: AsyncSession, refresh_token: str) -> Session | None:
    """根据刷新令牌获取会话"""
    result = await db.execute(
        select(Session).filter(
            and_(
                Session.refresh_token == refresh_token,
                Session.expires_at > datetime.now(timezone.utc),
            )
        )
    )
    return result.scalar_one_or_none()


async def invalidate_session(db: AsyncSession, session_id: str) -> None:
    """使会话失效"""
    await db.execute(delete(Session).filter(Session.id == session_id))


async def invalidate_user_sessions(db: AsyncSession, user_id: str) -> None:
    """使用户所有会话失效"""
    await db.execute(delete(Session).filter(Session.user_id == user_id))


async def get_user_access_context(db: AsyncSession, user: User) -> AccessContext:
    """获取用户访问上下文"""
    role_codes = [role.code for role in user.roles]
    permissions = []
    for role in user.roles:
        permissions.extend([perm.code for perm in role.permissions])

    department_ids = [dept.id for dept in user.departments]
    group_ids = [group.id for group in user.groups]

    return AccessContext(
        user_id=user.id,
        tenant_id=user.tenant_id,
        roles=role_codes,
        permissions=permissions,
        data_scopes={
            "department": department_ids,
            "group": group_ids,
        },
    )


async def login(
    db: AsyncSession, request: Request, login_data: LoginRequest
) -> LoginResponse:
    """用户登录"""
    username = login_data.username
    password = login_data.password

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    if await check_login_lockout(db, username):
        await create_login_log(
            db,
            username=username,
            success=False,
            failure_reason="账号已被锁定，请稍后再试",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthenticationError(
            message="账号已被锁定，请稍后再试",
            details={"retry_after": LOGIN_LOCKOUT_DURATION_MINUTES * 60},
        )

    user = await get_user_by_username(db, username)
    if not user:
        await create_login_log(
            db,
            username=username,
            success=False,
            failure_reason="用户名或密码错误",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthenticationError(message="用户名或密码错误")

    if not verify_password(password, user.password_hash):
        await create_login_log(
            db,
            username=username,
            success=False,
            failure_reason="用户名或密码错误",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthenticationError(message="用户名或密码错误")

    access_context = await get_user_access_context(db, user)

    access_token_payload = {
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "roles": access_context.roles,
        "permissions": access_context.permissions,
        "data_scopes": access_context.data_scopes,
    }

    access_token = create_access_token(access_token_payload)
    refresh_token_payload = {"sub": user.id}
    refresh_token = create_refresh_token(refresh_token_payload)

    session = await create_user_session(
        db,
        user=user,
        refresh_token=refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    await create_login_log(
        db,
        username=username,
        success=True,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session.id,
    )

    logger.info("login_success", user_id=user.id, username=username, ip_address=ip_address)

    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.security.access_token_expire_minutes * 60,
        ),
    )


async def refresh_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """刷新访问令牌"""
    payload = verify_token(refresh_token, "refresh")
    if not payload:
        raise AuthenticationError(message="刷新令牌无效")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError(message="令牌格式错误")

    session = await get_session_by_refresh_token(db, refresh_token)
    if not session:
        raise AuthenticationError(message="会话不存在或已过期")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise AuthenticationError(message="用户不存在")

    access_context = await get_user_access_context(db, user)

    access_token_payload = {
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "roles": access_context.roles,
        "permissions": access_context.permissions,
        "data_scopes": access_context.data_scopes,
    }

    new_access_token = create_access_token(access_token_payload)
    new_refresh_token = create_refresh_token({"sub": user.id})

    session.refresh_token = new_refresh_token
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.security.refresh_token_expire_days)
    await db.flush()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.security.access_token_expire_minutes * 60,
    )


async def logout(db: AsyncSession, access_token: str) -> None:
    """退出登录"""
    payload = verify_token(access_token, "access")
    if not payload:
        return

    user_id = payload.get("sub")
    if user_id:
        await invalidate_user_sessions(db, user_id)
        logger.info("logout_success", user_id=user_id)


async def get_current_user(db: AsyncSession, user_id: str) -> UserResponse:
    """获取当前用户信息"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ResourceNotFoundError(resource_type="用户", resource_id=user_id)

    return UserResponse.model_validate(user)


async def register_user(db: AsyncSession, register_data: dict[str, Any]) -> UserResponse:
    """注册用户"""
    username = register_data.get("username")
    email = register_data.get("email")
    password = register_data.get("password")

    if not username or not email or not password:
        raise AuthenticationError(message="用户名、邮箱和密码不能为空")

    existing_user = await db.execute(
        select(User).filter(
            (User.username == username) | (User.email == email)
        )
    )
    if existing_user.scalar_one_or_none():
        raise AuthenticationError(message="用户名或邮箱已被使用")

    hashed_password = get_password_hash(password)

    user = User(
        id=f"usr_{uuid.uuid4().hex[:16]}",
        tenant_id="default",
        username=username,
        email=email,
        password_hash=hashed_password,
        full_name=register_data.get("full_name"),
        is_active=True,
        is_superuser=False,
        created_by="system",
    )
    db.add(user)
    await db.flush()

    logger.info("user_registered", user_id=user.id, username=username, email=email)

    return UserResponse.model_validate(user)


async def change_password(
    db: AsyncSession, user_id: str, old_password: str, new_password: str
) -> None:
    """修改密码"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ResourceNotFoundError(resource_type="用户", resource_id=user_id)

    if not verify_password(old_password, user.password_hash):
        raise AuthenticationError(message="旧密码错误")

    if len(new_password) < 6:
        raise AuthenticationError(message="密码长度至少为6位")

    user.password_hash = get_password_hash(new_password)
    user.updated_by = user_id
    await db.flush()

    await invalidate_user_sessions(db, user_id)

    logger.info("password_changed", user_id=user_id)


async def reset_password(db: AsyncSession, email: str) -> None:
    """重置密码"""
    result = await db.execute(
        select(User).filter(
            and_(
                User.email == email,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    temporary_password = f"Temp@{uuid.uuid4().hex[:8]}"
    user.password_hash = get_password_hash(temporary_password)
    user.updated_by = "system"
    await db.flush()

    await invalidate_user_sessions(db, user.id)

    logger.info("password_reset_requested", user_id=user.id, email=email)