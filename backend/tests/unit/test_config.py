"""
配置测试
"""
import pytest
from app.core.config import AppSettings


def test_settings_defaults():
    """测试配置默认值"""
    settings = AppSettings()
    assert settings.name == "rag-knowledge"
    assert settings.debug is False
    assert settings.environment == "development"


def test_settings_log_level_validation():
    """测试日志级别验证"""
    settings = AppSettings(log_level="debug")
    assert settings.log_level == "DEBUG"

    with pytest.raises(ValueError):
        AppSettings(log_level="invalid")


def test_database_url():
    """测试数据库 URL 生成"""
    settings = AppSettings(
        database=AppSettings.__pydantic_fields__["database"].default.__class__(
            host="localhost",
            port=5432,
            name="test",
            user="user",
            password="pass",
        )
    )
    assert "postgresql" in settings.database.async_url
    assert "localhost:5432" in settings.database.async_url


def test_redis_url():
    """测试 Redis URL 生成"""
    settings = AppSettings(
        redis=AppSettings.__pydantic_fields__["redis"].default.__class__(
            host="localhost",
            port=6379,
            password="",
            db=0,
        )
    )
    assert settings.redis.url == "redis://localhost:6379/0"
