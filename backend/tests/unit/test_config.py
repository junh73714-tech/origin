"""
配置测试
"""
import pytest
from app.core.config import AppSettings


def test_settings_defaults():
    """测试配置默认值"""
    settings = AppSettings()
    assert settings.app.name == "rag-knowledge"
    assert settings.app.debug is False
    assert settings.app.environment == "development"


def test_settings_log_level_validation():
    """测试日志级别验证"""
    settings = AppSettings(log_level="debug")
    assert settings.app.log_level == "DEBUG"

    with pytest.raises(ValueError):
        AppSettings(log_level="invalid")


def test_database_url():
    """测试数据库 URL 生成"""
    settings = AppSettings(
        DATABASE_HOST="localhost",
        DATABASE_PORT=5432,
        DATABASE_NAME="test",
        DATABASE_USER="user",
        DATABASE_PASSWORD="pass",
    )
    assert "postgresql" in settings.database.async_url
    assert "localhost:5432" in settings.database.async_url


def test_redis_url():
    """测试 Redis URL 生成"""
    settings = AppSettings(
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_PASSWORD="",
        REDIS_DB=0,
    )
    assert settings.redis.url == "redis://localhost:6379/0"
