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


@auth_router.post("/seed", tags=["认证"])
async def seed_data_api(
    db: DBSession,
    current_user_id: RequiredUser,
):
    """
    生成种子数据（仅限开发环境）

    创建测试用户、角色、权限、部门、知识库权限和临时授权样本数据。
    用于成员6进行真实DB联调测试。
    """
    from scripts.seed_data import (
        create_users,
        create_roles,
        create_permissions,
        assign_user_roles,
        assign_role_permissions,
        create_departments,
        create_user_groups,
        assign_user_departments,
        assign_user_groups,
        create_kb_permissions,
        create_temporary_grants,
        create_data_scopes,
    )

    users = await create_users(db)
    roles = await create_roles(db)
    permissions = await create_permissions(db)
    await assign_user_roles(db, users, roles)
    await assign_role_permissions(db, roles, permissions)
    departments = await create_departments(db)
    groups = await create_user_groups(db)
    await assign_user_departments(db, users, departments)
    await assign_user_groups(db, users, groups)
    await create_kb_permissions(db, users, roles, departments)
    await create_temporary_grants(db, users)
    await create_data_scopes(db)

    await db.commit()

    return success_response(
        data={
            "users": [
                {"username": "admin", "password": "admin123", "role": "超级管理员"},
                {"username": "user", "password": "user123", "role": "普通员工(有KB权限)"},
                {"username": "nokb", "password": "nokb123", "role": "无KB权限用户"},
                {"username": "locked", "password": "locked123", "role": "被锁定用户"},
            ],
            "kb_permissions": [
                "kb-public: employee角色可读",
                "kb-tech: 技术部可读",
                "kb-confidential: 超级管理员可读",
                "kb-all: user用户可读",
            ],
            "temporary_grants": [
                "user: kb-temp 7天有效",
                "nokb: doc-temp-001 1天有效",
                "user: kb-expired 已过期",
            ],
        },
        message="种子数据生成成功",
    )