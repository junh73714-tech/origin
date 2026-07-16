"""
应用入口点
"""
import uvicorn

from app.core.config import settings


def main():
    """启动应用"""
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.debug,
        log_level=settings.app.log_level.lower(),
    )


if __name__ == "__main__":
    main()
