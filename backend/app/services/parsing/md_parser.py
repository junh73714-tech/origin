"""
Markdown文档解析器

使用 markdown 库提取纯文本，同时保留标题、段落、列表、代码块等结构。

成员5主责：Markdown解析实现
"""
import re
from typing import BinaryIO

from app.services.parsing.base import (
    BaseParser,
    ParseResult,
    PageElement,
    ParseQuality,
)


class MarkdownParser(BaseParser):
    """Markdown文档解析器

    解析Markdown格式文档，提取:
    - 标题层级（H1-H6）
    - 段落文本
    - 列表项
    - 代码块（转为普通文本保留）
    """

    # Markdown标题正则
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    # 无序列表
    UL_PATTERN = re.compile(r"^[\s]*[-*+]\s+(.+)$", re.MULTILINE)
    # 有序列表
    OL_PATTERN = re.compile(r"^[\s]*\d+\.\s+(.+)$", re.MULTILINE)
    # 代码块
    CODE_BLOCK_PATTERN = re.compile(r"```[^`]*```", re.DOTALL)

    @property
    def supported_format(self) -> str:
        return "md"

    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        """解析Markdown文件"""
        result = ParseResult(file_type="md")

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("gbk", errors="replace")

        # 提取结构
        page_element = PageElement(page_number=1)

        # 提取标题
        position = 0
        for match in self.HEADING_PATTERN.finditer(text):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            page_element.headings.append({
                "level": level,
                "text": heading_text,
                "position": match.start(),
            })

        # 提取纯文本（去除Markdown标记）
        clean_text = self._strip_markdown(text)
        page_element.text = clean_text
        result.total_chars = len(clean_text)
        result.total_pages = 1

        # 按空行拆分段落
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        page_element.paragraphs = paragraphs

        # 提取列表项
        for match in self.UL_PATTERN.finditer(text):
            page_element.lists.append(match.group(1).strip())
        for match in self.OL_PATTERN.finditer(text):
            page_element.lists.append(match.group(1).strip())

        result.pages.append(page_element)
        return result

    def parse_stream(self, stream: BinaryIO, filename: str = "") -> ParseResult:
        """流式解析Markdown"""
        data = stream.read()
        return self.parse(data, filename)

    def _strip_markdown(self, text: str) -> str:
        """去除Markdown标记，保留纯文本"""
        # 移除代码块
        text = self.CODE_BLOCK_PATTERN.sub("", text)

        # 移除图片 ![...](...)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

        # 移除链接 [...](...) 保留文本
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

        # 移除标题标记
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # 移除加粗/斜体
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)

        # 移除行内代码
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # 移除块引用标记
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

        # 移除水平线
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        return text
