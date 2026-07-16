"""
PDF文档解析器

使用 pdfplumber 作为主解析引擎，PyMuPDF 作为备选。
提取文本、页码、标题、段落、表格等结构信息。
OCR不可用时的扫描PDF标记为degraded质量。

成员5主责：PDF解析实现
"""
import io
from typing import BinaryIO

from app.core.exceptions import DocumentProcessingError
from app.services.parsing.base import (
    BaseParser,
    ParseResult,
    PageElement,
    TableElement,
    ParseWarning,
    ParseQuality,
)


class PDFParser(BaseParser):
    """PDF文档解析器"""

    @property
    def supported_format(self) -> str:
        return "pdf"

    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        """解析PDF文件"""
        result = ParseResult(file_type="pdf")
        file_obj = io.BytesIO(data)

        try:
            import pdfplumber
            with pdfplumber.open(file_obj) as pdf:
                result.total_pages = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, 1):
                    page_element = PageElement(page_number=page_num)

                    # 提取文本
                    page_text = page.extract_text() or ""
                    page_element.text = page_text
                    page_element.raw_offset = result.total_chars
                    result.total_chars += len(page_text)

                    # 提取表格
                    raw_tables = page.extract_tables()
                    if raw_tables:
                        for table_data in raw_tables:
                            if not table_data:
                                continue
                            headers = [str(c) if c else "" for c in table_data[0]]
                            rows = [
                                [str(c) if c else "" for c in row]
                                for row in table_data[1:]
                            ]
                            table_elem = TableElement(
                                headers=headers,
                                rows=rows,
                                page=page_num,
                            )
                            page_element.tables.append(table_elem)
                            result.tables.append(table_elem)

                    # 检测扫描PDF（无文本但可能有图片）
                    if len(page_text.strip()) == 0:
                        # 检查是否有图片
                        page_images = page.images if hasattr(page, "images") else []
                        if len(page_images) > 0:
                            result.warnings.append(ParseWarning(
                                code="SCANNED_PAGE",
                                message=f"第{page_num}页可能为扫描图片，需要OCR处理",
                                page=page_num,
                            ))
                            result.quality = ParseQuality.DEGRADED

                    result.pages.append(page_element)

            # 提取标题（基于常见规则：短行、粗体标记等）
            self._detect_headings(result)

        except ImportError:
            # pdfplumber不可用时使用PyMuPDF备用
            result = self._parse_with_pymupdf(data, filename)
        except Exception as e:
            raise DocumentProcessingError(
                message=f"PDF解析失败: {str(e)}",
                details={"filename": filename, "error": str(e)},
            )

        return result

    def parse_stream(self, stream: BinaryIO, filename: str = "") -> ParseResult:
        """流式解析PDF（读取全部数据后委托给parse）"""
        data = stream.read()
        return self.parse(data, filename)

    def _parse_with_pymupdf(self, data: bytes, filename: str) -> ParseResult:
        """使用PyMuPDF作为备选解析引擎"""
        import fitz
        result = ParseResult(file_type="pdf")
        doc = fitz.open(stream=data, filetype="pdf")

        try:
            result.total_pages = doc.page_count

            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_element = PageElement(page_number=page_num + 1)

                # 提取文本
                page_text = page.get_text()
                page_element.text = page_text
                page_element.raw_offset = result.total_chars
                result.total_chars += len(page_text)

                # 提取表格
                tabs = page.find_tables()
                if tabs and tabs.tables:
                    for table in tabs.tables:
                        data_rows = table.extract()
                        if not data_rows:
                            continue
                        headers = [str(c) if c else "" for c in data_rows[0]]
                        rows = [
                            [str(c) if c else "" for c in row]
                            for row in data_rows[1:]
                        ]
                        result.tables.append(TableElement(
                            headers=headers, rows=rows, page=page_num + 1,
                        ))

                result.pages.append(page_element)

            self._detect_headings(result)

        finally:
            doc.close()

        return result

    def _detect_headings(self, result: ParseResult) -> None:
        """基于启发式规则识别文档标题

        规则:
        1. 短行（少于80字符）且不以句号结尾
        2. 全行加粗或全大写
        3. 以编号开头（如 "1.", "1.1", "第一章"等）
        """
        import re

        heading_patterns = [
            re.compile(r"^第[一二三四五六七八九十\d]+[章节条款]"),  # 中文章节
            re.compile(r"^\d+(\.\d+)*\s"),  # 数字编号
            re.compile(r"^[IVX]+\.\s"),     # 罗马数字
        ]

        for page in result.pages:
            lines = page.text.split("\n")
            position = page.raw_offset

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    position += len(line) + 1
                    continue

                # 判断是否为标题
                is_heading = False
                level = 3  # 默认级别

                # 规则1: 匹配标题模式
                for pattern in heading_patterns:
                    if pattern.match(stripped):
                        is_heading = True
                        level = 1 if re.match(r"^第[一二三四五六七八九十\d]+章", stripped) else 2
                        break

                # 规则2: 短行判断
                if not is_heading and len(stripped) < 80 and not stripped.endswith("。"):
                    is_heading = True
                    level = 3

                if is_heading:
                    page.headings.append({
                        "level": level,
                        "text": stripped,
                        "position": position,
                    })

                position += len(line) + 1


class OCRProvider:
    """OCR服务提供者接口

    用于处理扫描PDF等需要OCR的文档。
    当前为接口定义，具体实现需要接入OCR服务。
    """

    async def process_image(self, image_data: bytes, language: str = "chi_sim+eng") -> str:
        """
        对图片进行OCR识别

        Args:
            image_data: 图片二进制数据
            language: OCR语言设置

        Returns:
            str: 识别的文本

        Note:
            当前为占位实现。生产环境需接入Tesseract OCR、PaddleOCR
            或其他OCR服务。OCR不可用时返回空字符串并标记为degraded。
        """
        # 占位实现：OCR服务不可用时返回空
        return ""
