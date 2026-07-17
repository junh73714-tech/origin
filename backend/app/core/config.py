"""
应用配置模块
统一管理所有配置项，支持环境变量覆盖
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    host: str = "localhost"
    port: int = 5432
    name: str = "rag_knowledge"
    user: str = "rag_user"
    password: str = ""
    pool_size: int = 20
    max_overflow: int = 10

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class RedisSettings(BaseSettings):
    """Redis 配置"""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class MinIOSettings(BaseSettings):
    """MinIO 配置"""
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    bucket_documents: str = "documents"
    bucket_temp: str = "temp"

    model_config = SettingsConfigDict(env_prefix="MINIO_")


class OpenSearchSettings(BaseSettings):
    """OpenSearch 配置"""
    host: str = "localhost"
    port: int = 9200
    user: str = "admin"
    password: str = "admin"
    scheme: str = "http"

    @property
    def url(self) -> str:
        return f"{self.scheme}://{self.user}:{self.password}@{self.host}:{self.port}"

    model_config = SettingsConfigDict(env_prefix="OPENSEARCH_")


class LLMSettings(BaseSettings):
    """LLM 配置"""
    provider: Literal["openai", "anthropic", "azure", "local"] = "openai"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2000

    model_config = SettingsConfigDict(env_prefix="OPENAI_")


class EmbeddingSettings(BaseSettings):
    """Embedding 配置"""
    provider: Literal["openai", "local"] = "openai"
    model: str = "text-embedding-3-small"
    dimension: int = 1536
    batch_size: int = 100

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")


class RerankerSettings(BaseSettings):
    """Reranker 配置"""
    provider: Literal["openai", "cohere", "local"] = "cohere"
    model: str = "cohere-rerank-4"
    top_n: int = 10
    api_key: str = ""

    model_config = SettingsConfigDict(env_prefix="RERANKER_")


class CelerySettings(BaseSettings):
    """Celery 配置"""
    broker_url: str = ""
    result_backend: str = ""

    @property
    def resolved_broker_url(self) -> str:
        if self.broker_url:
            return self.broker_url
        # 自动从 Redis 配置派生
        from app.core.config import settings
        redis_url = settings.redis.url
        return f"{redis_url}/1"  # 使用 Redis DB 1 作为 Celery broker

    @property
    def resolved_result_backend(self) -> str:
        if self.result_backend:
            return self.result_backend
        # 自动从 Redis 配置派生
        from app.core.config import settings
        redis_url = settings.redis.url
        return f"{redis_url}/2"  # 使用 Redis DB 2 作为 Celery result backend

    model_config = SettingsConfigDict(env_prefix="CELERY_")


class SecuritySettings(BaseSettings):
    """安全配置"""
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(env_prefix="APP_")


class AppSettings(BaseSettings):
    """应用主配置"""
    name: str = "rag-knowledge"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # 子配置（添加类型注解以兼容 Pydantic v2）
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    minio: MinIOSettings = MinIOSettings()
    opensearch: OpenSearchSettings = OpenSearchSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    reranker: RerankerSettings = RerankerSettings()
    celery: CelerySettings = CelerySettings()
    security: SecuritySettings = SecuritySettings()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> AppSettings:
    """获取配置单例"""
    return AppSettings()


# 全局配置实例
settings = get_settings()
