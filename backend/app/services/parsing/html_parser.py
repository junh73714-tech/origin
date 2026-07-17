"""
HTML文档解析器

使用 BeautifulSoup 提取文本、标题、段落、列表、表格等结构。

成员5主责：HTML解析实现
"""
from typing import BinaryIO

from app.core.exceptions import DocumentProcessingError
from app.services.parsing.base import (
    BaseParser,
    ParseResult,
    PageElement,
    TableElement,
    ParseQuality,
)


class HTMLParser(BaseParser):
    """HTML文档解析器

    提取结构化内容:
    - 标题 (h1-h6)
    - 段落 (<p>)
    - 列表 (<ul>, <ol>)
    - 表格 (<table>)
    """

    @property
    def supported_format(self) -> str:
        return "html"

    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        """解析HTML文件"""
        result = ParseResult(file_type="html")

        try:
            from bs4 import BeautifulSoup

            # 尝试多种编码
            for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
                try:
                    html_text = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise DocumentProcessingError(
                    message="HTML文件编码无法识别",
                    details={"filename": filename},
                )

            soup = BeautifulSoup(html_text, "html.parser")

            # 移除script和style标签
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()

            page_element = PageElement(page_number=1)
            position = 0

            # 提取标题
            for level in range(1, 7):
                for heading in soup.find_all(f"h{level}"):
                    text = heading.get_text(strip=True)
                    if text:
                        page_element.headings.append({
                            "level": level,
                            "text": text,
                            "position": position,
                        })
                        position += len(text) + 1

            # 提取段落
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text:
                    page_element.paragraphs.append(text)
                    position += len(text) + 1

            # 提取列表
            for ul in soup.find_all(["ul", "ol"]):
                for li in ul.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        page_element.lists.append(text)

            # 提取表格
            for table in soup.find_all("table"):
                table_elem = self._extract_table(table)
                if table_elem:
                    page_element.tables.append(table_elem)
                    result.tables.append(table_elem)

            # 获取完整文本
            page_element.text = soup.get_text(separator="\n", strip=True)
            result.total_chars = len(page_element.text)
            result.total_pages = 1
            result.pages.append(page_element)

        except Exception as e:
            raise DocumentProcessingError(
                message=f"HTML解析失败: {str(e)}",
                details={"filename": filename, "error": str(e)},
            )

        return result

    def parse_stream(self, stream: BinaryIO, filename: str = "") -> ParseResult:
        """流式解析HTML"""
        data = stream.read()
        return self.parse(data, filename)

    def _extract_table(self, table_tag) -> TableElement | None:
        """从BeautifulSoup的table标签提取TableElement"""
        rows_data = []
        for row in table_tag.find_all("tr"):
            cells = []
            for cell in row.find_all(["th", "td"]):
                cells.append(cell.get_text(strip=True))
            if cells:
                rows_data.append(cells)

        if not rows_data:
            return None

        headers = rows_data[0] if len(rows_data) > 1 else []
        data_rows = rows_data[1:] if len(rows_data) > 1 else rows_data

        return TableElement(headers=headers, rows=data_rows)
