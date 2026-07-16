"""
MinIO存储服务单元测试

测试文件校验、哈希计算、存储路径生成、MinIO操作。
MinIO客户端使用mock隔离外部依赖。
"""
import io
import os
import hashlib
import pytest
from unittest.mock import MagicMock, patch

from app.core.exceptions import ValidationError, StorageError


# =============================================================================
# SHA-256 哈希计算测试
# =============================================================================

class TestSHA256Calculation:

    def test_calculate_sha256_bytes(self):
        """测试计算字节数据的SHA-256"""
        from app.services.storage import calculate_sha256

        data = b"Hello, World!"
        result = calculate_sha256(data)
        expected = hashlib.sha256(data).hexdigest()
        assert result == expected
        assert len(result) == 64  # SHA-256产生64个十六进制字符

    def test_calculate_sha256_empty(self):
        """测试计算空数据的SHA-256"""
        from app.services.storage import calculate_sha256

        result = calculate_sha256(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_calculate_sha256_deterministic(self):
        """测试SHA-256计算的确定性"""
        from app.services.storage import calculate_sha256

        data = b"deterministic test data"
        r1 = calculate_sha256(data)
        r2 = calculate_sha256(data)
        assert r1 == r2

    def test_calculate_file_sha256(self):
        """测试计算文件SHA-256"""
        import tempfile
        from app.services.storage import calculate_file_sha256

        content = b"test file content for hashing"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(content)
            temp_path = f.name

        try:
            result = calculate_file_sha256(temp_path)
            expected = hashlib.sha256(content).hexdigest()
            assert result == expected
        finally:
            os.unlink(temp_path)


# =============================================================================
# 文件校验测试
# =============================================================================

class TestFileValidation:

    def test_valid_pdf(self):
        """测试合法的PDF文件"""
        from app.services.storage import validate_file
        # 不应抛异常
        validate_file("document.pdf", 1024 * 1024, "application/pdf")

    def test_valid_docx(self):
        """测试合法的DOCX文件"""
        from app.services.storage import validate_file
        validate_file("document.docx", 1024 * 100, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_valid_txt(self):
        """测试合法的TXT文件"""
        from app.services.storage import validate_file
        validate_file("notes.txt", 1024, "text/plain")

    def test_valid_md(self):
        """测试合法的Markdown文件"""
        from app.services.storage import validate_file
        validate_file("readme.md", 2048, "text/markdown")

    def test_valid_html(self):
        """测试合法的HTML文件"""
        from app.services.storage import validate_file
        validate_file("page.html", 4096, "text/html")

    def test_invalid_extension(self):
        """测试不支持的文件扩展名"""
        from app.services.storage import validate_file

        with pytest.raises(ValidationError) as exc:
            validate_file("script.exe", 1024, "application/x-msdownload")
        assert "不支持的文件类型" in exc.value.message

    def test_invalid_extension_no_mime(self):
        """测试不支持的文件扩展名（无MIME）"""
        from app.services.storage import validate_file

        with pytest.raises(ValidationError):
            validate_file("image.png", 1024)

    def test_empty_file(self):
        """测试空文件"""
        from app.services.storage import validate_file

        with pytest.raises(ValidationError) as exc:
            validate_file("empty.pdf", 0, "application/pdf")
        assert "文件内容为空" in exc.value.message

    def test_negative_file_size(self):
        """测试负数文件大小"""
        from app.services.storage import validate_file

        with pytest.raises(ValidationError):
            validate_file("doc.pdf", -1, "application/pdf")

    def test_oversize_file(self):
        """测试超大文件（使用环境变量覆盖默认值以加速测试）"""
        from app.services.storage import validate_file

        # 默认限制100MB，设置小限制来测试
        with patch.dict(os.environ, {"DOCUMENT_MAX_SIZE_MB": "1"}):
            with pytest.raises(ValidationError) as exc:
                validate_file("big.pdf", 2 * 1024 * 1024, "application/pdf")
            assert "文件大小超过限制" in exc.value.message

    def test_mime_extension_mismatch(self):
        """测试MIME类型与扩展名不匹配"""
        from app.services.storage import validate_file

        with pytest.raises(ValidationError) as exc:
            validate_file("doc.pdf", 1024, "text/plain")
        assert "不匹配" in exc.value.message

    def test_markdown_mime_variants(self):
        """测试Markdown的MIME变体"""
        from app.services.storage import validate_file
        # text/markdown 和 text/plain 对.md文件都应通过
        validate_file("readme.md", 1024, "text/markdown")
        validate_file("readme.md", 1024, "text/x-markdown")
        validate_file("readme.md", 1024, "text/plain")

    def test_uppercase_extension(self):
        """测试大写扩展名"""
        from app.services.storage import validate_file
        # 扩展名大小写不敏感
        validate_file("DOC.PDF", 1024, "application/pdf")

    def test_without_mime(self):
        """测试不提供MIME类型时仅校验扩展名和大小"""
        from app.services.storage import validate_file
        # 不提供MIME时跳过MIME校验
        validate_file("document.txt", 1024)


# =============================================================================
# 存储路径生成测试
# =============================================================================

class TestStorageKeyGeneration:

    def test_build_storage_key(self):
        """测试构建存储路径"""
        from app.services.storage import build_storage_key

        key = build_storage_key(
            tenant_id="tenant-001",
            knowledge_base_id="kb-001",
            document_id="doc-001",
            version=1,
            file_hash="abc123def456",
            extension=".pdf",
        )
        assert key == "tenant-001/kb-001/doc-001/v1/abc123def456.pdf"

    def test_build_storage_key_without_dot(self):
        """测试扩展名无点号时自动补充"""
        from app.services.storage import build_storage_key

        key = build_storage_key(
            tenant_id="t1", knowledge_base_id="kb1", document_id="d1",
            version=3, file_hash="hash", extension="txt",
        )
        assert key == "t1/kb1/d1/v3/hash.txt"

    def test_build_storage_key_version_two(self):
        """测试第二版本的存储路径"""
        from app.services.storage import build_storage_key

        key = build_storage_key(
            tenant_id="t1", knowledge_base_id="kb1", document_id="d1",
            version=2, file_hash="newhash", extension=".docx",
        )
        assert key == "t1/kb1/d1/v2/newhash.docx"

    def test_storage_key_uniqueness(self):
        """测试不同哈希产生不同路径（重复文件识别的基础）"""
        from app.services.storage import build_storage_key

        k1 = build_storage_key("t1", "kb1", "d1", 1, "hash_a", ".pdf")
        k2 = build_storage_key("t1", "kb1", "d1", 1, "hash_b", ".pdf")
        assert k1 != k2


# =============================================================================
# MinIO存储服务测试（Mock）
# =============================================================================

class TestMinioStorageService:
    """MinIO存储服务测试（使用mock隔离MinIO）"""

    @pytest.fixture
    def mock_minio_client(self):
        """创建mock的MinIO客户端"""
        with patch("app.services.storage.Minio") as mock_minio_class:
            mock_client = MagicMock()
            mock_minio_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def storage_service(self, mock_minio_client):
        """创建MinioStorageService实例"""
        from app.services.storage import MinioStorageService
        return MinioStorageService()

    def test_upload_file_success(self, storage_service, mock_minio_client):
        """测试成功上传文件"""
        mock_minio_client.bucket_exists.return_value = True

        result = storage_service.upload_file(
            file_data=b"test content",
            storage_key="t1/kb1/d1/v1/hash.txt",
            content_type="text/plain",
        )

        assert result["key"] == "t1/kb1/d1/v1/hash.txt"
        assert result["size"] == 12
        mock_minio_client.put_object.assert_called_once()

    def test_upload_ensures_bucket(self, storage_service, mock_minio_client):
        """测试上传时自动创建存储桶"""
        mock_minio_client.bucket_exists.return_value = False

        storage_service.upload_file(
            file_data=b"data",
            storage_key="t1/kb1/d1/v1/hash.txt",
        )

        mock_minio_client.make_bucket.assert_called_once()

    def test_upload_to_temp_bucket(self, storage_service, mock_minio_client):
        """测试上传到临时桶"""
        mock_minio_client.bucket_exists.return_value = True

        result = storage_service.upload_file(
            file_data=b"temp data",
            storage_key="temp_file_123",
            bucket=storage_service.bucket_temp,
        )

        assert result["bucket"] == storage_service.bucket_temp

    def test_upload_failure_raises_storage_error(self, storage_service, mock_minio_client):
        """测试上传失败抛出StorageError"""
        from minio.error import S3Error
        mock_minio_client.bucket_exists.return_value = True
        mock_minio_client.put_object.side_effect = S3Error(
            response=MagicMock(), code="InternalError",
            message="Connection refused", resource="key",
            request_id="req1", host_id="host1",
        )

        with pytest.raises(StorageError):
            storage_service.upload_file(
                file_data=b"data",
                storage_key="key",
            )

    def test_download_file_success(self, storage_service, mock_minio_client):
        """测试成功下载文件"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"downloaded content"
        mock_minio_client.get_object.return_value = mock_response

        data = storage_service.download_file("t1/kb1/d1/v1/hash.txt")

        assert data == b"downloaded content"
        mock_minio_client.get_object.assert_called_once()

    def test_download_file_not_found(self, storage_service, mock_minio_client):
        """测试下载不存在的文件"""
        from minio.error import S3Error
        mock_minio_client.get_object.side_effect = S3Error(
            response=MagicMock(), code="NoSuchKey", message="Not found",
            resource="key", request_id="req1", host_id="host1",
        )

        with pytest.raises(StorageError) as exc:
            storage_service.download_file("nonexistent/key")
        assert "不存在" in exc.value.message

    def test_delete_file_success(self, storage_service, mock_minio_client):
        """测试成功删除文件"""
        result = storage_service.delete_file("t1/kb1/d1/v1/hash.txt")

        assert result is True
        mock_minio_client.remove_object.assert_called_once()

    def test_file_exists_true(self, storage_service, mock_minio_client):
        """测试文件存在"""
        assert storage_service.file_exists("existing/key") is True

    def test_file_exists_false(self, storage_service, mock_minio_client):
        """测试文件不存在"""
        from minio.error import S3Error
        mock_minio_client.stat_object.side_effect = S3Error(
            response=MagicMock(), code="NoSuchKey", message="Not found",
            resource="key", request_id="req1", host_id="host1",
        )

        assert storage_service.file_exists("nonexistent/key") is False

    def test_get_presigned_url(self, storage_service, mock_minio_client):
        """测试生成预签名URL"""
        mock_minio_client.presigned_get_object.return_value = "http://minio:9000/doc/key?token=xxx"

        url = storage_service.get_presigned_url("t1/kb1/d1/v1/hash.pdf")

        assert url.startswith("http://")

    def test_get_file_info(self, storage_service, mock_minio_client):
        """测试获取文件元信息"""
        mock_stat = MagicMock()
        mock_stat.size = 1024
        mock_stat.etag = "abc123"
        mock_stat.last_modified = None
        mock_stat.content_type = "application/pdf"
        mock_stat.metadata = {}
        mock_minio_client.stat_object.return_value = mock_stat

        info = storage_service.get_file_info("t1/kb1/d1/v1/hash.pdf")

        assert info is not None
        assert info["size"] == 1024
        assert info["content_type"] == "application/pdf"

    def test_get_file_info_not_found(self, storage_service, mock_minio_client):
        """测试获取不存在文件的元信息"""
        from minio.error import S3Error
        mock_minio_client.stat_object.side_effect = S3Error(
            response=MagicMock(), code="NoSuchKey", message="Not found",
            resource="key", request_id="req1", host_id="host1",
        )

        info = storage_service.get_file_info("nonexistent/key")
        assert info is None

    def test_cleanup_temp_file(self, storage_service, mock_minio_client):
        """测试清理临时文件"""
        assert storage_service.cleanup_temp_file("temp/key") is True

    def test_cleanup_temp_file_graceful_failure(self, storage_service, mock_minio_client):
        """测试临时文件清理失败不抛异常"""
        from minio.error import S3Error
        mock_minio_client.remove_object.side_effect = S3Error(
            response=MagicMock(), code="AccessDenied",
            message="Access denied", resource="key",
            request_id="req1", host_id="host1",
        )

        result = storage_service.cleanup_temp_file("temp/key")
        assert result is False


# =============================================================================
# 常量测试
# =============================================================================

class TestConstants:

    def test_allowed_extensions(self):
        """测试允许的扩展名列表包含一期支持的格式"""
        from app.services.storage import ALLOWED_EXTENSIONS

        assert ".pdf" in ALLOWED_EXTENSIONS
        assert ".docx" in ALLOWED_EXTENSIONS
        assert ".txt" in ALLOWED_EXTENSIONS
        assert ".md" in ALLOWED_EXTENSIONS
        assert ".html" in ALLOWED_EXTENSIONS

    def test_extension_mime_map_coverage(self):
        """测试每个允许的扩展名都有对应的MIME映射"""
        from app.services.storage import ALLOWED_EXTENSIONS, EXTENSION_MIME_MAP

        for ext in ALLOWED_EXTENSIONS:
            assert ext in EXTENSION_MIME_MAP, f"扩展名{ext}缺少MIME映射"

    def test_bucket_names_from_config(self):
        """测试存储桶名称来自配置"""
        from app.services.storage import MinioStorageService

        service = MinioStorageService()
        assert len(service.bucket_documents) > 0
        assert len(service.bucket_temp) > 0
