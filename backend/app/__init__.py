"""
应用包。

避免在 import app 时强制加载 FastAPI 应用与数据库引擎，
以便单元测试可直接导入子模块。公共变更标记成员1评审。
"""

__all__ = ["app"]


def __getattr__(name: str):
    if name == "app":
        from app.main import app as _app

        return _app
    raise AttributeError(name)
