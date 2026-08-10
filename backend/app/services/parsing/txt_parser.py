"""
TXT文档解析器

处理纯文本格式，识别段落结构。

成员5主责：TXT解析实现
"""
from typing import BinaryIO

from app.core.exceptions import DocumentProcessingError
from app.services.parsing.base import (
    BaseParser,
    ParseResult,
    PageElement,
    ParseQuality,
)


class TXTParser(BaseParser):
    """TXT文档解析器

    纯文本文件按段落(\n\n)拆分为结构单元。
    """

    # 常见文本编码尝试顺序
    ENCODINGS = ["utf-8", "gbk", "gb2312", "latin-1"]

    @property
    def supported_format(self) -> str:
        return "txt"

    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        """解析TXT文件（自动检测编码）"""
        result = ParseResult(file_type="txt")

        text = None
        used_encoding = None

        for encoding in self.ENCODINGS:
            try:
                text = data.decode(encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if text is None:
            raise DocumentProcessingError(
                message="TXT解析失败: 无法识别的文件编码",
                details={"filename": filename},
            )

        # 构建页面元素
        page_element = PageElement(page_number=1)
        page_element.text = text
        result.total_chars = len(text)
        result.total_pages = 1

        # 按空行拆分为段落
        paragraphs = self._split_paragraphs(text)
        page_element.paragraphs = paragraphs

        result.pages.append(page_element)

        # 记录编码信息
        result.metadata = {"encoding": used_encoding}

        return result

    def parse_stream(self, stream: BinaryIO, filename: str = "") -> ParseResult:
        """流式解析TXT"""
        data = stream.read()
        return self.parse(data, filename)

    def _split_paragraphs(self, text: str) -> list[str]:
        """按空行拆分为段落"""
        # 先按双换行拆分
        raw_paragraphs = text.split("\n\n")
        # 过滤空段落并去除首尾空白
        paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
        return paragraphs or [text.strip()]  # 至少保留一个段落
