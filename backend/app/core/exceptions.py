"""
自定义异常模块
定义业务异常和 HTTP 异常
"""
from typing import Any


class RAGKnowledgeException(Exception):
    """业务异常基类"""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(RAGKnowledgeException):
    """认证异常"""

    def __init__(
        self,
        message: str = "认证失败",
        details: dict[str, Any] | None = None,
    ):
        super().__init__("AUTH_ERROR", message, details)


class LoginLockedError(AuthenticationError):
    """登录锁定异常"""

    def __init__(
        self,
        message: str = "账户已被锁定，请稍后再试",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message=message, details=details)
        self.code = "AUTH_LOGIN_LOCKED"


class AuthorizationError(RAGKnowledgeException):
    """授权异常"""

    def __init__(
        self,
        message: str = "权限不足",
        details: dict[str, Any] | None = None,
    ):
        super().__init__("AUTHZ_ERROR", message, details)


class ResourceNotFoundError(RAGKnowledgeException):
    """资源不存在"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ):
        message = f"{resource_type} 不存在: {resource_id}"
        super().__init__("NOT_FOUND", message, details)


class DuplicateResourceError(RAGKnowledgeException):
    """资源重复"""

    def __init__(
        self,
        resource_type: str,
        identifier: str,
        details: dict[str, Any] | None = None,
    ):
        message = f"{resource_type} 已存在: {identifier}"
        super().__init__("DUPLICATE", message, details)


class ValidationError(RAGKnowledgeException):
    """数据验证异常"""

    def __init__(
        self,
        message: str = "数据验证失败",
        details: dict[str, Any] | None = None,
    ):
        super().__init__("VALIDATION_ERROR", message, details)


class BusinessStateError(RAGKnowledgeException):
    """业务状态异常"""

    def __init__(
        self,
        message: str,
        current_state: str | None = None,
        expected_state: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state
        super().__init__("STATE_ERROR", message, details)


class DocumentProcessingError(RAGKnowledgeException):
    """文档处理异常"""

    def __init__(
        self,
        message: str,
        document_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if document_id:
            details["document_id"] = document_id
        super().__init__("DOC_PROCESSING_ERROR", message, details)


class RetrievalError(RAGKnowledgeException):
    """检索异常"""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__("RETRIEVAL_ERROR", message, details)


class ModelAPIError(RAGKnowledgeException):
    """模型 API 异常"""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if provider:
            details["provider"] = provider
        super().__init__("MODEL_API_ERROR", message, details)


class StorageError(RAGKnowledgeException):
    """存储异常"""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__("STORAGE_ERROR", message, details)


class RateLimitError(RAGKnowledgeException):
    """限流异常"""

    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__("RATE_LIMIT", message, details)
