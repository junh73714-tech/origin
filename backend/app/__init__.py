"""
应用初始化
使用懒加载避免模块导入时触发完整的应用创建链
"""
# 懒加载 app，仅在直接访问 app 属性时触发
# 避免 import app.models 时触发整个应用初始化
__all__ = ["app"]

_app = None


def __getattr__(name):
    """懒加载模块属性"""
    if name == "app":
        global _app
        if _app is None:
            from app.main import app as _application
            _app = _application
        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
