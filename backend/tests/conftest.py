"""
后端测试初始化
"""
import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
