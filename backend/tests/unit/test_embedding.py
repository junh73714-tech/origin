"""
Embedding Provider 单元测试

测试共享 EmbeddingProvider 的功能和模型版本管理。
使用 mock 隔离 OpenAI API 调用。
"""
import pytest
from unittest.mock import MagicMock, patch


class TestEmbeddingProvider:

    @pytest.fixture
    def mock_embedding_response(self):
        """创建模拟的Embedding API响应"""
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1] * 1536
        mock_response.data = [mock_data]
        return mock_response

    @pytest.fixture
    def provider(self):
        """创建EmbeddingProvider（不发起真实API调用）"""
        with patch("app.providers.embedding.OpenAI"):
            from app.providers.embedding import EmbeddingProvider
            return EmbeddingProvider(
                model="text-embedding-3-small",
                api_key="test-key",
                base_url="https://test.api.com",
                dimension=1536,
                batch_size=10,
            )

    def test_get_model_info(self, provider):
        """测试获取模型信息"""
        info = provider.get_model_info()

        assert info["model"] == "text-embedding-3-small"
        assert info["dimension"] == 1536
        assert "model_version" in info
        assert len(info["model_version"]) == 8

    def test_model_version_stable(self, provider):
        """测试模型版本标识的稳定性"""
        with patch("app.providers.embedding.OpenAI"):
            from app.providers.embedding import EmbeddingProvider

            p1 = EmbeddingProvider(model="model-a", dimension=768, api_key="k", base_url="u")
            p2 = EmbeddingProvider(model="model-a", dimension=768, api_key="k", base_url="u")
            p3 = EmbeddingProvider(model="model-b", dimension=768, api_key="k", base_url="u")

            # 相同配置产生相同版本
            assert p1.model_version == p2.model_version
            # 不同模型产生不同版本
            assert p1.model_version != p3.model_version

    def test_embed_query_success(self, provider, mock_embedding_response):
        """测试成功生成查询Embedding"""
        provider.client.embeddings.create.return_value = mock_embedding_response

        vector = provider.embed_query("这是一个测试查询")

        assert len(vector) == 1536
        provider.client.embeddings.create.assert_called_once()

    def test_embed_query_empty_text(self, provider):
        """测试空文本查询"""
        with pytest.raises(Exception):
            provider.embed_query("")

    def test_embed_documents_batch(self, provider, mock_embedding_response):
        """测试批量文档Embedding"""
        # 模拟返回多个向量
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
        provider.client.embeddings.create.return_value = mock_response

        vectors = provider.embed_documents(["文本1", "文本2"])

        assert len(vectors) == 2
        assert len(vectors[0]) == 1536

    def test_embed_documents_empty_list(self, provider):
        """测试空文本列表"""
        vectors = provider.embed_documents([])
        assert vectors == []

    def test_embed_documents_splits_batches(self, provider):
        """测试大批量文本自动分批"""
        texts = [f"文本{i}" for i in range(25)]

        # 每次调用返回正确数量的向量（10个/批）
        def create_batch_response(model=None, input=None, **kwargs):
            batch_size = len(input)
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(batch_size)]
            return mock_response

        provider.client.embeddings.create.side_effect = create_batch_response

        vectors = provider.embed_documents(texts)

        assert len(vectors) == 25
        # 应被调用3次（10+10+5）
        assert provider.client.embeddings.create.call_count == 3

    def test_verify_dimension(self, provider):
        """测试向量维度校验"""
        valid = [[0.1] * 1536, [0.2] * 1536]
        assert provider.verify_dimension(valid) is True

        invalid = [[0.1] * 768]
        assert provider.verify_dimension(invalid) is False

    def test_retry_on_failure(self, provider):
        """测试API调用重试"""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary error")
            mock_response = MagicMock()
            mock_data = MagicMock()
            mock_data.embedding = [0.1] * 1536
            mock_response.data = [mock_data]
            return mock_response

        provider.client.embeddings.create.side_effect = side_effect

        vectors = provider.embed_documents(["测试文本"])
        assert len(vectors) == 1
        assert call_count[0] == 3  # 2次失败 + 1次成功

    def test_retry_exhausted(self, provider):
        """测试重试耗尽后抛出异常"""
        provider.client.embeddings.create.side_effect = Exception("Persistent error")

        with pytest.raises(Exception):
            provider.embed_documents(["测试文本"])

        # 应重试3次
        assert provider.client.embeddings.create.call_count == 3
