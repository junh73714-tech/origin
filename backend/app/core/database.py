"""
数据库连接模块
支持异步 SQLAlchemy 2.x
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


# 创建异步引擎
engine = create_async_engine(
    settings.database.async_url,
    echo=settings.debug,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_pre_ping=True,
)

# 创建会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    依赖注入：获取数据库会话
    用于 FastAPI 路由中
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    上下文管理器：获取数据库会话
    用于 Celery 任务等非 FastAPI 场景
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库连接"""
    async with engine.begin() as conn:
        # 可以在这里创建扩展
        # await conn.execute(create_pg_vector_extension())
        pass


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
