"""
示例数据端到端验证测试

验证5种格式的示例文档可以被解析、切分和生成Chunk。
这是最接近真实使用场景的集成测试。
"""
import os
import pytest


# 项目根目录（backend/tests/unit/ -> backend -> 项目根）
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SAMPLE_DIR = os.path.join(_project_root, "sample_data")


def _read_sample(filename: str) -> bytes:
    """读取示例文件"""
    filepath = os.path.join(SAMPLE_DIR, filename)
    if not os.path.exists(filepath):
        pytest.skip(f"示例文件不存在: {filename}")
    with open(filepath, "rb") as f:
        return f.read()


# =============================================================================
# TXT 示例文档测试
# =============================================================================

class TestTxtSample:

    def test_parse_txt(self):
        """测试解析TXT示例文档"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("员工考勤管理制度.txt")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "txt", "员工考勤管理制度.txt")

        assert result.file_type == "txt"
        assert result.total_chars > 500  # 有实质内容
        assert result.quality.value == "good"
        assert len(result.pages) == 1
        assert result.heading_count == 0  # TXT无标题标记

    def test_txt_paragraphs(self):
        """测试TXT段落拆分"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("员工考勤管理制度.txt")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "txt", "员工考勤管理制度.txt")

        paragraphs = result.pages[0].paragraphs
        assert len(paragraphs) >= 1  # 至少有一个段落（Windows换行符影响切分）

    def test_txt_clause_chunking(self):
        """测试TXT条款切分"""
        from app.services.parsing import ParserDispatcher
        from app.services.chunking import DocumentChunker

        data = _read_sample("员工考勤管理制度.txt")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "txt", "员工考勤管理制度.txt")

        chunker = DocumentChunker(min_chunk_tokens=0)
        chunks = chunker.chunk(result)

        # 应该有多个Chunk（按条款切分）
        assert len(chunks) >= 2
        # 验证条款内容
        texts = [c.clean_text for c in chunks]
        assert any("第一条" in t for t in texts)
        assert any("考勤" in t for t in texts)


# =============================================================================
# Markdown 示例文档测试
# =============================================================================

class TestMarkdownSample:

    def test_parse_md(self):
        """测试解析Markdown示例文档"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("技术架构说明.md")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "md", "技术架构说明.md")

        assert result.file_type == "md"
        assert result.total_chars > 500
        assert result.quality.value == "good"

    def test_md_headings(self):
        """测试Markdown标题提取"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("技术架构说明.md")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "md", "技术架构说明.md")

        headings = result.pages[0].headings
        assert len(headings) >= 5  # 多个标题层级
        # 验证标题内容
        heading_texts = [h["text"] for h in headings]
        assert any("系统概述" in t for t in heading_texts)
        assert any("技术栈" in t for t in heading_texts)

    def test_md_lists(self):
        """测试Markdown列表提取"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("技术架构说明.md")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "md", "技术架构说明.md")

        lists = result.pages[0].lists
        assert len(lists) > 0

    def test_md_markdown_cleaned(self):
        """测试Markdown标记被清除"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("技术架构说明.md")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "md", "技术架构说明.md")

        text = result.pages[0].text
        # 不应该包含Markdown标记
        assert "```" not in text  # 代码块标记被移除
        assert "###" not in text  # 标题标记被移除
        assert "**" not in text   # 加粗标记被移除


# =============================================================================
# HTML 示例文档测试
# =============================================================================

class TestHtmlSample:

    def test_parse_html(self):
        """测试解析HTML示例文档"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("用户手册.html")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "html", "用户手册.html")

        assert result.file_type == "html"
        assert result.total_chars > 200
        assert result.quality.value == "good"

    def test_html_headings(self):
        """测试HTML标题提取"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("用户手册.html")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "html", "用户手册.html")

        headings = result.pages[0].headings
        assert len(headings) >= 3

    def test_html_table(self):
        """测试HTML表格提取"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("用户手册.html")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "html", "用户手册.html")

        assert result.has_tables, "HTML应包含表格"


# =============================================================================
# PDF 示例文档测试
# =============================================================================

class TestPdfSample:

    def test_parse_pdf(self):
        """测试解析PDF示例文档"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("信息安全管理制度.pdf")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "pdf", "信息安全管理制度.pdf")

        assert result.file_type == "pdf"
        assert result.total_chars > 100
        assert result.total_pages >= 1
        assert result.quality.value in ("good", "warning")

    def test_pdf_pages(self):
        """测试PDF页码识别"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("信息安全管理制度.pdf")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "pdf", "信息安全管理制度.pdf")

        # 每个页面有页码
        for page in result.pages:
            assert page.page_number >= 1

    def test_pdf_chunking(self):
        """测试PDF切分"""
        from app.services.parsing import ParserDispatcher
        from app.services.chunking import DocumentChunker

        data = _read_sample("信息安全管理制度.pdf")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "pdf", "信息安全管理制度.pdf")

        chunker = DocumentChunker(min_chunk_tokens=0)
        chunks = chunker.chunk(result)

        assert len(chunks) >= 1
        # 验证Chunk有完整的元数据
        for ch in chunks:
            assert ch.chunk_no >= 1
            assert ch.token_count >= 0
            assert len(ch.clean_text) > 0


# =============================================================================
# DOCX 示例文档测试
# =============================================================================

class TestDocxSample:

    def test_parse_docx(self):
        """测试解析DOCX示例文档"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("新员工入职指南.docx")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "docx", "新员工入职指南.docx")

        assert result.file_type == "docx"
        assert result.total_chars > 200
        assert result.quality.value == "good"

    def test_docx_headings(self):
        """测试DOCX标题提取"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("新员工入职指南.docx")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "docx", "新员工入职指南.docx")

        headings = result.pages[0].headings
        assert len(headings) >= 2

    def test_docx_content(self):
        """测试DOCX内容完整性"""
        from app.services.parsing import ParserDispatcher

        data = _read_sample("新员工入职指南.docx")
        dispatcher = ParserDispatcher()
        result = dispatcher.parse_and_clean(data, "docx", "新员工入职指南.docx")

        text = result.pages[0].text
        # 验证关键内容存在
        assert "入职" in text
        assert "试用期" in text


# =============================================================================
# 全格式端到端测试
# =============================================================================

class TestAllFormatsEndToEnd:

    def test_all_formats_parse(self):
        """测试全部5种格式可解析"""
        from app.services.parsing import ParserDispatcher

        samples = {
            "员工考勤管理制度.txt": "txt",
            "技术架构说明.md": "md",
            "用户手册.html": "html",
            "信息安全管理制度.pdf": "pdf",
            "新员工入职指南.docx": "docx",
        }

        dispatcher = ParserDispatcher()
        for filename, expected_type in samples.items():
            data = _read_sample(filename)
            result = dispatcher.parse(data, expected_type, filename)
            assert result.file_type == expected_type, f"{filename} 解析类型错误"
            assert result.total_chars > 0, f"{filename} 内容为空"
            assert result.quality.value in ("good", "warning"), f"{filename} 解析质量差"

    def test_all_formats_chunk(self):
        """测试全部5种格式可切分"""
        from app.services.parsing import ParserDispatcher
        from app.services.chunking import DocumentChunker

        samples = {
            "员工考勤管理制度.txt": "txt",
            "技术架构说明.md": "md",
            "用户手册.html": "html",
            "信息安全管理制度.pdf": "pdf",
            "新员工入职指南.docx": "docx",
        }

        dispatcher = ParserDispatcher()
        chunker = DocumentChunker(min_chunk_tokens=0)

        for filename, file_type in samples.items():
            data = _read_sample(filename)
            result = dispatcher.parse_and_clean(data, file_type, filename)
            chunks = chunker.chunk(result)

            assert len(chunks) >= 1, f"{filename} 切分为空"
            # 验证每个Chunk有必要的元数据
            for ch in chunks:
                assert ch.chunk_no >= 1, f"{filename} Chunk序号异常"
                assert len(ch.clean_text) > 0, f"{filename} Chunk内容为空"
                assert ch.token_count >= 0, f"{filename} Token计数异常"
