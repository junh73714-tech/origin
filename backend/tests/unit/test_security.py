"""
安全工具测试
"""
import pytest
from datetime import timedelta

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
    AccessContext,
)


def test_password_hash():
    """测试密码哈希"""
    password = "test_password123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert len(hashed) > 0


def test_password_verify():
    """测试密码验证"""
    password = "test_password123"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_access_token():
    """测试访问令牌创建和验证"""
    data = {"sub": "user123", "tenant_id": "tenant1"}
    token = create_access_token(data)

    assert token is not None
    assert len(token) > 0

    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "user123"
    assert payload["tenant_id"] == "tenant1"
    assert payload["type"] == "access"


def test_refresh_token():
    """测试刷新令牌"""
    data = {"sub": "user123"}
    token = create_refresh_token(data)

    assert token is not None
    payload = verify_token(token, token_type="refresh")
    assert payload is not None
    assert payload["type"] == "refresh"


def test_token_expiry():
    """测试令牌过期"""
    data = {"sub": "user123"}
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))

    payload = verify_token(token)
    assert payload is None


def test_access_context():
    """测试访问上下文"""
    ctx = AccessContext(
        user_id="user1",
        tenant_id="tenant1",
        roles=["admin"],
        permissions=["read", "write"],
        data_scopes={"document": ["doc1", "doc2"]},
    )

    assert ctx.has_permission("read") is True
    assert ctx.has_permission("delete") is False
    assert ctx.has_role("admin") is True
    assert ctx.has_role("user") is False
    assert ctx.can_access_data("document", "doc1") is True
    assert ctx.can_access_data("document", "doc3") is False
    assert ctx.is_super_admin() is False


def test_access_context_super_admin():
    """测试超级管理员"""
    ctx = AccessContext(
        user_id="admin",
        tenant_id="system",
        roles=["super_admin"],
        permissions=["*"],
        data_scopes={"*": ["*"]},
    )

    assert ctx.is_super_admin() is True
    assert ctx.has_permission("anything") is True


def test_access_context_system():
    """测试系统上下文"""
    ctx = AccessContext.system()
    assert ctx.user_id == "system"
    assert ctx.is_super_admin() is False
    assert "*" in ctx.permissions
