"""
文档解析服务单元测试

测试5种格式解析器和调度器。
包含文本提取、结构识别、清洗规则和错误处理。
"""
import io
import pytest

from app.services.parsing.base import ParseResult, ParseQuality, TableElement, ParseWarning


# =============================================================================
# PDF解析测试
# =============================================================================

class TestPDFParser:

    def _create_simple_pdf(self) -> bytes:
        """创建一个简单的PDF用于测试"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            c.drawString(100, 750, "第一章 概述")
            c.drawString(100, 730, "这是一个测试文档。")
            c.drawString(100, 710, "用于验证PDF解析功能。")
            c.showPage()
            c.drawString(100, 750, "第二章 详细说明")
            c.drawString(100, 730, "这是第二页的内容。")
            c.drawString(100, 710, "包含更多测试文本。")
            c.save()
            return buf.getvalue()
        except ImportError:
            return None

    def test_pdf_parser_import(self):
        """测试PDF解析器可导入"""
        from app.services.parsing.pdf_parser import PDFParser
        parser = PDFParser()
        assert parser.supported_format == "pdf"

    def test_parse_pdf_bytes(self):
        """测试解析PDF文件"""
        from app.services.parsing.pdf_parser import PDFParser

        pdf_data = self._create_simple_pdf()
        if pdf_data is None:
            pytest.skip("reportlab未安装")

        parser = PDFParser()
        result = parser.parse(pdf_data, "test.pdf")

        assert result.file_type == "pdf"
        assert result.total_pages >= 1
        assert result.total_chars > 0
        assert result.quality == ParseQuality.GOOD

    def test_parse_pdf_with_tables(self):
        """测试解析包含表格的PDF"""
        from app.services.parsing.pdf_parser import PDFParser

        pdf_data = self._create_simple_pdf()
        if pdf_data is None:
            pytest.skip("reportlab未安装")

        parser = PDFParser()
        result = parser.parse(pdf_data, "test.pdf")

        # 基本验证
        assert isinstance(result, ParseResult)
        assert len(result.pages) > 0

    def test_parse_stream(self):
        """测试流式解析PDF"""
        from app.services.parsing.pdf_parser import PDFParser

        pdf_data = self._create_simple_pdf()
        if pdf_data is None:
            pytest.skip("reportlab未安装")

        parser = PDFParser()
        stream = io.BytesIO(pdf_data)
        result = parser.parse_stream(stream, "test.pdf")

        assert result.file_type == "pdf"
        assert result.total_pages >= 1


# =============================================================================
# DOCX解析测试
# =============================================================================

class TestDOCXParser:

    def _create_simple_docx(self) -> bytes:
        """创建一个简单的DOCX用于测试"""
        try:
            from docx import Document
            doc = Document()
            doc.add_heading("测试文档", level=1)
            doc.add_paragraph("这是一个测试段落。")
            doc.add_heading("第一节", level=2)
            doc.add_paragraph("第一节的内容。")
            doc.add_paragraph("另一个段落。")
            buf = io.BytesIO()
            doc.save(buf)
            return buf.getvalue()
        except Exception:
            return None

    def test_docx_parser_import(self):
        """测试DOCX解析器可导入"""
        from app.services.parsing.docx_parser import DOCXParser
        parser = DOCXParser()
        assert parser.supported_format == "docx"

    def test_parse_docx(self):
        """测试解析DOCX文件"""
        from app.services.parsing.docx_parser import DOCXParser

        data = self._create_simple_docx()
        if data is None:
            pytest.skip("python-docx创建测试文件失败")

        parser = DOCXParser()
        result = parser.parse(data, "test.docx")

        assert result.file_type == "docx"
        assert result.total_chars > 0
        assert len(result.pages) > 0
        assert isinstance(result, ParseResult)

    def test_parse_docx_headings(self):
        """测试DOCX标题提取"""
        from app.services.parsing.docx_parser import DOCXParser

        data = self._create_simple_docx()
        if data is None:
            pytest.skip("python-docx创建测试文件失败")

        parser = DOCXParser()
        result = parser.parse(data, "test.docx")

        # DOCX应该至少识别到一个标题
        headings = result.pages[0].headings
        assert len(headings) > 0


# =============================================================================
# TXT解析测试
# =============================================================================

class TestTXTParser:

    def test_parse_utf8(self):
        """测试解析UTF-8编码TXT"""
        from app.services.parsing.txt_parser import TXTParser

        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        parser = TXTParser()
        result = parser.parse(text.encode("utf-8"), "test.txt")

        assert result.file_type == "txt"
        assert result.total_chars > 0
        assert len(result.pages) == 1
        assert len(result.pages[0].paragraphs) == 3

    def test_parse_gbk(self):
        """测试解析GBK编码TXT"""
        from app.services.parsing.txt_parser import TXTParser

        # 包含中文的文本
        text = "企业管理制度\n\n第一章 总则\n\n本制度适用于全体员工。"
        parser = TXTParser()
        result = parser.parse(text.encode("gbk"), "test.txt")

        assert result.total_chars > 0
        assert result.metadata.get("encoding") == "gbk"

    def test_parse_single_paragraph(self):
        """测试解析单段落TXT"""
        from app.services.parsing.txt_parser import TXTParser

        text = "只有一段的文本内容。"
        parser = TXTParser()
        result = parser.parse(text.encode("utf-8"), "test.txt")

        assert len(result.pages[0].paragraphs) == 1

    def test_parse_empty_text(self):
        """测试解析空TXT"""
        from app.services.parsing.txt_parser import TXTParser

        parser = TXTParser()
        result = parser.parse(b"", "empty.txt")

        assert result.total_chars == 0


# =============================================================================
# Markdown解析测试
# =============================================================================

class TestMarkdownParser:

    def test_parse_headings(self):
        """测试Markdown标题提取"""
        from app.services.parsing.md_parser import MarkdownParser

        md_text = """# 第一章 概述

## 1.1 背景

这是背景介绍。

## 1.2 目标

这是目标说明。

### 1.2.1 具体目标

详细内容。
"""
        parser = MarkdownParser()
        result = parser.parse(md_text.encode("utf-8"), "test.md")

        assert result.file_type == "md"
        headings = result.pages[0].headings
        assert len(headings) >= 4  # H1, H2x2, H3

        # 验证标题层级
        assert headings[0]["level"] == 1
        assert headings[0]["text"] == "第一章 概述"

    def test_parse_lists(self):
        """测试Markdown列表提取"""
        from app.services.parsing.md_parser import MarkdownParser

        md_text = """# 功能列表

- 功能A
- 功能B
- 功能C

1. 第一步
2. 第二步
3. 第三步
"""
        parser = MarkdownParser()
        result = parser.parse(md_text.encode("utf-8"), "test.md")

        lists = result.pages[0].lists
        assert len(lists) >= 6  # 3个无序 + 3个有序

    def test_markdown_clean_text(self):
        """测试Markdown清洗"""
        from app.services.parsing.md_parser import MarkdownParser

        md_text = """# 标题

这是**加粗**文字。

这是*斜体*文字。

[链接文本](https://example.com)
"""
        parser = MarkdownParser()
        result = parser.parse(md_text.encode("utf-8"), "test.md")

        text = result.pages[0].text
        assert "加粗" in text
        assert "https://" not in text  # 链接URL应被移除


# =============================================================================
# HTML解析测试
# =============================================================================

class TestHTMLParser:

    def test_parse_basic_html(self):
        """测试解析基本HTML"""
        from app.services.parsing.html_parser import HTMLParser

        html = """<!DOCTYPE html>
<html>
<head><title>测试</title></head>
<body>
<h1>标题一</h1>
<p>这是第一段。</p>
<h2>标题二</h2>
<p>这是第二段。</p>
<ul>
    <li>项目A</li>
    <li>项目B</li>
</ul>
</body>
</html>
"""
        parser = HTMLParser()
        result = parser.parse(html.encode("utf-8"), "test.html")

        assert result.file_type == "html"
        assert result.total_chars > 0
        assert len(result.pages) == 1

    def test_html_headings(self):
        """测试HTML标题提取"""
        from app.services.parsing.html_parser import HTMLParser

        html = "<h1>主标题</h1><p>内容</p><h2>副标题</h2><p>更多内容</p>"
        parser = HTMLParser()
        result = parser.parse(html.encode("utf-8"), "test.html")

        headings = result.pages[0].headings
        assert len(headings) == 2
        assert headings[0]["level"] == 1
        assert headings[1]["level"] == 2

    def test_html_script_removal(self):
        """测试HTML script标签被移除"""
        from app.services.parsing.html_parser import HTMLParser

        html = "<h1>标题</h1><script>alert('xss')</script><p>安全内容</p>"
        parser = HTMLParser()
        result = parser.parse(html.encode("utf-8"), "test.html")

        text = result.pages[0].text
        assert "alert" not in text
        assert "xss" not in text
        assert "安全内容" in text

    def test_html_table(self):
        """测试HTML表格提取"""
        from app.services.parsing.html_parser import HTMLParser

        html = """<table>
<tr><th>姓名</th><th>年龄</th></tr>
<tr><td>张三</td><td>30</td></tr>
<tr><td>李四</td><td>25</td></tr>
</table>"""
        parser = HTMLParser()
        result = parser.parse(html.encode("utf-8"), "test.html")

        # 验证表格被提取
        assert result.has_tables


# =============================================================================
# 调度器测试
# =============================================================================

class TestParserDispatcher:

    def test_get_parser_pdf(self):
        """测试获取PDF解析器"""
        from app.services.parsing.dispatcher import get_parser
        from app.services.parsing.pdf_parser import PDFParser

        parser = get_parser("pdf")
        assert isinstance(parser, PDFParser)

    def test_get_parser_docx(self):
        """测试获取DOCX解析器"""
        from app.services.parsing.dispatcher import get_parser
        from app.services.parsing.docx_parser import DOCXParser

        parser = get_parser("docx")
        assert isinstance(parser, DOCXParser)

    def test_get_parser_txt(self):
        """测试获取TXT解析器"""
        from app.services.parsing.dispatcher import get_parser
        from app.services.parsing.txt_parser import TXTParser

        parser = get_parser("txt")
        assert isinstance(parser, TXTParser)

    def test_get_parser_md(self):
        """测试获取Markdown解析器"""
        from app.services.parsing.dispatcher import get_parser
        from app.services.parsing.md_parser import MarkdownParser

        parser = get_parser("md")
        assert isinstance(parser, MarkdownParser)

    def test_get_parser_html(self):
        """测试获取HTML解析器"""
        from app.services.parsing.dispatcher import get_parser
        from app.services.parsing.html_parser import HTMLParser

        parser = get_parser("html")
        assert isinstance(parser, HTMLParser)

    def test_get_parser_unsupported(self):
        """测试不支持的文件类型"""
        from app.services.parsing.dispatcher import get_parser

        with pytest.raises(ValueError) as exc:
            get_parser("exe")
        assert "不支持" in str(exc.value)

    def test_get_parser_case_insensitive(self):
        """测试文件类型大小写不敏感"""
        from app.services.parsing.dispatcher import get_parser
        from app.services.parsing.pdf_parser import PDFParser

        parser = get_parser("PDF")
        assert isinstance(parser, PDFParser)

    def test_dispatcher_parse(self):
        """测试调度器解析"""
        from app.services.parsing.dispatcher import ParserDispatcher

        dispatcher = ParserDispatcher()
        result = dispatcher.parse(
            data="段落一\n\n段落二\n\n段落三".encode("utf-8"),
            file_type="txt",
            filename="test.txt",
        )

        assert result.file_type == "txt"
        assert len(result.pages[0].paragraphs) == 3


# =============================================================================
# 清洗规则测试
# =============================================================================

class TestCleaning:

    def test_merge_broken_lines(self):
        """测试合并被错误拆分的行"""
        from app.services.parsing.dispatcher import ParserDispatcher

        text = "这是被错误拆分\n的段落的示例。"
        merged = ParserDispatcher._merge_broken_lines(text)
        assert "\n" not in merged

    def test_merge_preserves_headings(self):
        """测试合并时不破坏标题结构"""
        from app.services.parsing.dispatcher import ParserDispatcher

        text = "# 第一章\n这是正文内容的\n第一行。"
        merged = ParserDispatcher._merge_broken_lines(text)
        # 标题行应保留
        assert "# 第一章" in merged

    def test_normalize_whitespace(self):
        """测试空白规范化"""
        from app.services.parsing.dispatcher import ParserDispatcher

        text = "hello  world   test"
        normalized = ParserDispatcher._normalize_whitespace(text)
        assert "  " not in normalized  # 多空格被压缩
        assert normalized == "hello world test"

    def test_normalize_newlines(self):
        """测试换行压缩"""
        from app.services.parsing.dispatcher import ParserDispatcher

        text = "段落一\n\n\n\n\n段落二"
        normalized = ParserDispatcher._normalize_whitespace(text)
        # 多个空行被压缩
        assert "\n\n\n" not in normalized

    def test_clean_result(self):
        """测试完整清洗流程"""
        from app.services.parsing.dispatcher import ParserDispatcher, _register_parsers
        from app.services.parsing.base import ParseResult, PageElement, ParseQuality

        result = ParseResult(file_type="txt")
        page = PageElement(page_number=1)
        page.text = "  多余的   空白  \n\n\n\n  第二段  "
        result.pages.append(page)
        result.total_chars = len(page.text)

        dispatcher = ParserDispatcher()
        dispatcher.clean_result(result)

        assert "    " not in result.pages[0].text
        assert "\n\n\n" not in result.pages[0].text


# =============================================================================
# ParseResult 属性测试
# =============================================================================

class TestParseResult:

    def test_full_text(self):
        """测试完整文本拼接"""
        from app.services.parsing.base import PageElement

        result = ParseResult(file_type="txt")
        p1 = PageElement(page_number=1, text="第一页内容")
        p2 = PageElement(page_number=2, text="第二页内容")
        result.pages = [p1, p2]

        full = result.full_text
        assert "第一页内容" in full
        assert "第二页内容" in full

    def test_has_tables(self):
        """测试表格检测"""
        result = ParseResult(file_type="pdf")
        assert result.has_tables is False

        result.tables.append(TableElement(headers=["A"], rows=[["1"]]))
        assert result.has_tables is True

    def test_has_errors(self):
        """测试错误检测"""
        result = ParseResult(file_type="pdf", quality=ParseQuality.ERROR)
        assert result.has_errors is True

        result.quality = ParseQuality.GOOD
        assert result.has_errors is False

    def test_heading_count(self):
        """测试标题计数"""
        from app.services.parsing.base import PageElement

        result = ParseResult(file_type="html")
        page = PageElement(page_number=1)
        page.headings = [
            {"level": 1, "text": "H1", "position": 0},
            {"level": 2, "text": "H2", "position": 10},
            {"level": 2, "text": "H2", "position": 20},
        ]
        result.pages.append(page)

        assert result.heading_count == 3
