"""
MinIO 对象存储服务

提供文件上传、下载、删除、预签名URL以及安全校验功能。
所有原始文件统一存储到 MinIO，key 格式为: {tenant}/{kb}/{doc}/{version}/{hash}.{ext}

成员5主责：MinIO存储集成、文件安全校验、哈希计算
"""
import hashlib
import os
import uuid
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.exceptions import StorageError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

# 一期支持的文档格式
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".htm"}

# 文件扩展名与MIME类型映射（用于校验文件内容与扩展名一致）
EXTENSION_MIME_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
}

# 允许的MIME类型（含变体）
ALLOWED_MIME_TYPES = {
    # PDF
    "application/pdf",
    # DOCX
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # DOC
    "application/msword",
    # TXT
    "text/plain",
    # Markdown
    "text/markdown",
    "text/x-markdown",
    # HTML
    "text/html",
}


def calculate_sha256(data: bytes) -> str:
    """计算数据的SHA-256哈希值"""
    return hashlib.sha256(data).hexdigest()


def calculate_file_sha256(file_path: str) -> str:
    """计算文件的SHA-256哈希值（流式读取，支持大文件）"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def validate_file(filename: str, file_size: int, mime_type: str | None = None) -> None:
    """
    文件安全校验

    校验规则:
    1. 扩展名必须在允许列表中
    2. 文件大小不超过配置的最大值（默认100MB）
    3. 如果提供了MIME类型，校验扩展名与MIME类型一致

    Args:
        filename: 文件名
        file_size: 文件大小（字节）
        mime_type: 声明的MIME类型（可选）

    Raises:
        ValidationError: 校验失败
    """
    ext = os.path.splitext(filename)[1].lower()

    # 校验扩展名
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            message=f"不支持的文件类型: {ext}，支持的格式: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            details={"filename": filename, "extension": ext},
        )

    # 校验文件大小（默认最大100MB，可通过环境变量配置）
    max_size = int(os.getenv("DOCUMENT_MAX_SIZE_MB", "100")) * 1024 * 1024
    if file_size <= 0:
        raise ValidationError(
            message="文件内容为空",
            details={"filename": filename, "file_size": file_size},
        )
    if file_size > max_size:
        raise ValidationError(
            message=f"文件大小超过限制({max_size // (1024*1024)}MB)",
            details={"filename": filename, "file_size": file_size, "max_size": max_size},
        )

    # 校验MIME类型（如果提供了）
    if mime_type and ext in EXTENSION_MIME_MAP:
        expected_mime = EXTENSION_MIME_MAP[ext]
        # Markdown的MIME类型可能有变体
        if ext == ".md":
            if mime_type not in ("text/markdown", "text/x-markdown", "text/plain"):
                raise ValidationError(
                    message=f"文件扩展名({ext})与MIME类型({mime_type})不匹配",
                    details={"filename": filename, "expected_mime": expected_mime, "actual_mime": mime_type},
                )
        elif ext == ".html":
            if mime_type not in ("text/html",):
                raise ValidationError(
                    message=f"文件扩展名({ext})与MIME类型({mime_type})不匹配",
                    details={"filename": filename, "expected_mime": expected_mime, "actual_mime": mime_type},
                )
        elif mime_type != expected_mime:
            raise ValidationError(
                message=f"文件扩展名({ext})与MIME类型({mime_type})不匹配",
                details={"filename": filename, "expected_mime": expected_mime, "actual_mime": mime_type},
            )


def build_storage_key(
    tenant_id: str,
    knowledge_base_id: str,
    document_id: str,
    version: int,
    file_hash: str,
    extension: str,
) -> str:
    """
    构建MinIO存储路径

    Key格式: {tenant_id}/{knowledge_base_id}/{document_id}/v{version}/{file_hash}{extension}

    这种层级结构便于按租户和知识库进行存储隔离和批量管理。
    """
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return f"{tenant_id}/{knowledge_base_id}/{document_id}/v{version}/{file_hash}{ext}"


class MinioStorageService:
    """MinIO对象存储服务

    封装MinIO客户端操作，提供文件上传、下载、删除等功能。
    所有操作带错误处理和日志记录。
    """

    def __init__(self):
        """初始化MinIO客户端"""
        minio_config = settings.minio
        self.client = Minio(
            endpoint=minio_config.endpoint,
            access_key=minio_config.access_key,
            secret_key=minio_config.secret_key,
            secure=minio_config.secure,
        )
        self.bucket_documents = minio_config.bucket_documents
        self.bucket_temp = minio_config.bucket_temp

    def _ensure_bucket(self, bucket_name: str) -> None:
        """确保存储桶存在，不存在则创建"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info("bucket_created", bucket=bucket_name)
        except S3Error as e:
            raise StorageError(
                message=f"MinIO存储桶操作失败: {e.message}",
                details={"bucket": bucket_name, "error": str(e)},
            )

    def upload_file(
        self,
        file_data: bytes,
        storage_key: str,
        content_type: str | None = None,
        bucket: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict:
        """
        上传文件到MinIO

        Args:
            file_data: 文件二进制数据
            storage_key: 存储路径(key)
            content_type: 文件MIME类型
            bucket: 存储桶名称（默认使用documents桶）
            metadata: 自定义元数据

        Returns:
            dict: {"bucket": str, "key": str, "size": int, "etag": str}

        Raises:
            StorageError: 上传失败
        """
        bucket_name = bucket or self.bucket_documents
        self._ensure_bucket(bucket_name)

        import io
        file_obj = io.BytesIO(file_data)
        file_size = len(file_data)

        try:
            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=storage_key,
                data=file_obj,
                length=file_size,
                content_type=content_type or "application/octet-stream",
                metadata=metadata,
            )
            logger.info(
                "file_uploaded",
                bucket=bucket_name,
                key=storage_key,
                size=file_size,
                etag=result.etag,
            )
            return {
                "bucket": bucket_name,
                "key": storage_key,
                "size": file_size,
                "etag": result.etag,
            }
        except S3Error as e:
            logger.error(
                "file_upload_failed",
                bucket=bucket_name,
                key=storage_key,
                error=str(e),
            )
            raise StorageError(
                message=f"文件上传到MinIO失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key, "error": str(e)},
            )

    def upload_file_stream(
        self,
        file_stream: BinaryIO,
        file_size: int,
        storage_key: str,
        content_type: str | None = None,
        bucket: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict:
        """
        流式上传文件到MinIO（适用于大文件，减少内存占用）

        Args:
            file_stream: 文件流对象
            file_size: 文件大小
            storage_key: 存储路径
            content_type: MIME类型
            bucket: 存储桶名称
            metadata: 自定义元数据

        Returns:
            dict: 上传结果信息
        """
        bucket_name = bucket or self.bucket_documents
        self._ensure_bucket(bucket_name)

        try:
            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=storage_key,
                data=file_stream,
                length=file_size,
                content_type=content_type or "application/octet-stream",
                metadata=metadata,
            )
            logger.info(
                "file_uploaded_stream",
                bucket=bucket_name,
                key=storage_key,
                size=file_size,
            )
            return {
                "bucket": bucket_name,
                "key": storage_key,
                "size": file_size,
                "etag": result.etag,
            }
        except S3Error as e:
            logger.error("file_upload_failed", bucket=bucket_name, key=storage_key, error=str(e))
            raise StorageError(
                message=f"文件上传到MinIO失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key},
            )

    def download_file(self, storage_key: str, bucket: str | None = None) -> bytes:
        """
        从MinIO下载文件

        Args:
            storage_key: 存储路径
            bucket: 存储桶名称

        Returns:
            bytes: 文件二进制数据

        Raises:
            StorageError: 下载失败或文件不存在
        """
        bucket_name = bucket or self.bucket_documents

        try:
            response = self.client.get_object(bucket_name, storage_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise StorageError(
                    message=f"文件不存在: {storage_key}",
                    details={"bucket": bucket_name, "key": storage_key},
                )
            raise StorageError(
                message=f"文件下载失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key},
            )

    def download_file_stream(self, storage_key: str, bucket: str | None = None):
        """
        流式下载文件（返回响应对象，调用方负责关闭）

        Args:
            storage_key: 存储路径
            bucket: 存储桶名称

        Returns:
            MinIO response object

        Raises:
            StorageError: 下载失败
        """
        bucket_name = bucket or self.bucket_documents

        try:
            return self.client.get_object(bucket_name, storage_key)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise StorageError(
                    message=f"文件不存在: {storage_key}",
                    details={"bucket": bucket_name, "key": storage_key},
                )
            raise StorageError(
                message=f"文件下载失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key},
            )

    def delete_file(self, storage_key: str, bucket: str | None = None) -> bool:
        """
        从MinIO删除文件

        Args:
            storage_key: 存储路径
            bucket: 存储桶名称

        Returns:
            bool: 删除成功返回True

        Raises:
            StorageError: 删除失败
        """
        bucket_name = bucket or self.bucket_documents

        try:
            self.client.remove_object(bucket_name, storage_key)
            logger.info("file_deleted", bucket=bucket_name, key=storage_key)
            return True
        except S3Error as e:
            logger.error("file_delete_failed", bucket=bucket_name, key=storage_key, error=str(e))
            raise StorageError(
                message=f"文件删除失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key},
            )

    def delete_files_batch(
        self, storage_keys: list[str], bucket: str | None = None
    ) -> dict[str, bool]:
        """
        批量删除文件

        Args:
            storage_keys: 存储路径列表
            bucket: 存储桶名称

        Returns:
            dict: {key: success} 每个key的删除结果
        """
        bucket_name = bucket or self.bucket_documents
        results = {}

        for key in storage_keys:
            try:
                self.client.remove_object(bucket_name, key)
                results[key] = True
            except S3Error as e:
                logger.warning("batch_delete_item_failed", key=key, error=str(e))
                results[key] = False

        return results

    def get_presigned_url(
        self,
        storage_key: str,
        bucket: str | None = None,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """
        获取文件的预签名访问URL

        Args:
            storage_key: 存储路径
            bucket: 存储桶名称
            expires: 过期时间

        Returns:
            str: 预签名URL
        """
        bucket_name = bucket or self.bucket_documents

        try:
            url = self.client.presigned_get_object(
                bucket_name, storage_key, expires=expires
            )
            return url
        except S3Error as e:
            raise StorageError(
                message=f"生成预签名URL失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key},
            )

    def file_exists(self, storage_key: str, bucket: str | None = None) -> bool:
        """
        检查文件是否存在

        Args:
            storage_key: 存储路径
            bucket: 存储桶名称
        """
        bucket_name = bucket or self.bucket_documents

        try:
            self.client.stat_object(bucket_name, storage_key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise StorageError(
                message=f"检查文件状态失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key},
            )

    def cleanup_temp_file(self, storage_key: str) -> bool:
        """
        清理临时文件（上传失败回滚时使用）

        临时文件存储在temp桶中。

        Args:
            storage_key: 临时文件路径
        """
        try:
            self.client.remove_object(self.bucket_temp, storage_key)
            logger.info("temp_file_cleaned", key=storage_key)
            return True
        except (S3Error, Exception):
            # 临时文件清理失败时只记录警告，不抛异常（清理属于尽力而为操作）
            logger.warning("temp_file_cleanup_failed", key=storage_key)
            return False

    def get_file_info(self, storage_key: str, bucket: str | None = None) -> dict | None:
        """
        获取文件元信息

        Args:
            storage_key: 存储路径
            bucket: 存储桶名称

        Returns:
            dict: 文件信息（size, etag, last_modified, content_type等）或None
        """
        bucket_name = bucket or self.bucket_documents

        try:
            stat = self.client.stat_object(bucket_name, storage_key)
            return {
                "key": storage_key,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "content_type": stat.content_type,
                "metadata": stat.metadata,
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise StorageError(
                message=f"获取文件信息失败: {e.message}",
                details={"bucket": bucket_name, "key": storage_key},
            )
