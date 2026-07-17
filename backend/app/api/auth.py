"""
成员4：认证路由
实现登录、注册、刷新令牌、退出、当前用户等接口
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status

from app.core.dependencies import DBSession, RequiredUser, get_current_user_id
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.responses import success_response
from fastapi.security import HTTPBearer
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    change_password,
    get_current_user,
    login,
    logout,
    refresh_token,
    register_user,
    reset_password,
)

auth_router = APIRouter()
router = auth_router  # main.py: from app.api.auth import router as auth_router
security = HTTPBearer(auto_error=False)


@auth_router.post("/login", response_model=LoginResponse, tags=["认证"])
async def login_api(
    request: Request,
    login_data: LoginRequest,
    db: DBSession,
):
    """用户登录"""
    result = await login(db, request, login_data)
    return result


@auth_router.post("/register", response_model=UserResponse, tags=["认证"])
async def register_api(
    register_data: RegisterRequest,
    db: DBSession,
):
    """用户注册"""
    result = await register_user(db, register_data.model_dump())
    return result


@auth_router.post("/refresh", response_model=TokenResponse, tags=["认证"])
async def refresh_api(
    refresh_data: RefreshTokenRequest,
    db: DBSession,
):
    """刷新访问令牌"""
    result = await refresh_token(db, refresh_data.refresh_token)
    return result


@auth_router.post("/logout", tags=["认证"])
async def logout_api(
    credentials: Annotated[HTTPBearer, Security(security)],
    db: DBSession,
):
    """退出登录"""
    access_token = credentials.credentials if credentials else None
    await logout(db, access_token or "")
    return success_response(message="退出成功")


@auth_router.get("/me", response_model=UserResponse, tags=["认证"])
async def get_me_api(
    user_id: RequiredUser,
    db: DBSession,
):
    """获取当前用户信息"""
    result = await get_current_user(db, user_id)
    return result


@auth_router.post("/change-password", tags=["认证"])
async def change_password_api(
    user_id: RequiredUser,
    change_data: ChangePasswordRequest,
    db: DBSession,
):
    """修改密码"""
    await change_password(
        db, user_id, change_data.old_password, change_data.new_password
    )
    return success_response(message="密码修改成功")


@auth_router.post("/reset-password", tags=["认证"])
async def reset_password_api(
    reset_data: ResetPasswordRequest,
    db: DBSession,
):
    """重置密码"""
    await reset_password(db, reset_data.email)
    return success_response(message="密码重置邮件已发送")