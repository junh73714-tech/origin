"""
解析器调度器和文档清洗服务

根据文件类型分派到对应的解析器，并对解析结果进行统一清洗。

成员5主责：解析调度和文档清洗
"""
import re
from app.services.parsing.base import BaseParser, ParseResult, ParseQuality
from app.services.parsing.pdf_parser import PDFParser
from app.services.parsing.docx_parser import DOCXParser
from app.services.parsing.txt_parser import TXTParser
from app.services.parsing.md_parser import MarkdownParser
from app.services.parsing.html_parser import HTMLParser


# 解析器注册表
_PARSER_REGISTRY: dict[str, BaseParser] = {}


def _register_parsers() -> None:
    """注册所有支持的解析器"""
    if _PARSER_REGISTRY:
        return
    parsers: list[BaseParser] = [
        PDFParser(),
        DOCXParser(),
        TXTParser(),
        MarkdownParser(),
        HTMLParser(),
    ]
    for parser in parsers:
        _PARSER_REGISTRY[parser.supported_format] = parser


def get_parser(file_type: str) -> BaseParser:
    """
    根据文件类型获取对应的解析器

    Args:
        file_type: 文件类型 (pdf/docx/txt/md/html)

    Returns:
        BaseParser: 对应的解析器实例

    Raises:
        ValueError: 不支持的文件类型
    """
    _register_parsers()
    file_type = file_type.lower().strip(".")
    parser = _PARSER_REGISTRY.get(file_type)
    if parser is None:
        supported = ", ".join(sorted(_PARSER_REGISTRY.keys()))
        raise ValueError(f"不支持的文件类型: {file_type}，支持的格式: {supported}")
    return parser


class ParserDispatcher:
    """解析器调度器

    根据文件类型自动选择合适的解析器，并执行解析。
    同时提供文档清洗功能。
    """

    def parse(self, data: bytes, file_type: str, filename: str = "") -> ParseResult:
        """
        根据文件类型解析文档

        Args:
            data: 文件二进制数据
            file_type: 文件类型 (pdf/docx/txt/md/html)
            filename: 原始文件名

        Returns:
            ParseResult: 解析结果
        """
        parser = get_parser(file_type)
        return parser.parse(data, filename)

    def parse_and_clean(
        self, data: bytes, file_type: str, filename: str = ""
    ) -> ParseResult:
        """
        解析文档并执行清洗

        清洗内容包括:
        - 去除重复页眉页脚
        - 合并被错误拆分的段落
        - 保留章节和列表结构
        - 去除多余空白

        Args:
            data: 文件二进制数据
            file_type: 文件类型
            filename: 原始文件名

        Returns:
            ParseResult: 清洗后的解析结果
        """
        result = self.parse(data, file_type, filename)
        if result.quality != ParseQuality.ERROR:
            self.clean_result(result)
        return result

    def clean_result(self, result: ParseResult) -> None:
        """对解析结果执行清洗"""
        for page in result.pages:
            # 1. 合并被错误拆分的段落（修复换行问题）
            page.text = self._merge_broken_lines(page.text)

            # 2. 去除多余空白
            page.text = self._normalize_whitespace(page.text)

            # 清洗段落
            page.paragraphs = [
                self._normalize_whitespace(p) for p in page.paragraphs
            ]

        # 3. 去除跨页重复的页眉页脚
        self._remove_duplicate_headers_footers(result)

    # -------------------------------------------------------------------------
    # 清洗规则实现
    # -------------------------------------------------------------------------

    @staticmethod
    def _merge_broken_lines(text: str) -> str:
        """
        合并被错误拆分的段落

        规则: 将以中文（或小写字母）结尾的行与下一行合并，
        如果下一行不以大写或标点开头。
        """
        lines = text.split("\n")
        merged = []
        i = 0
        while i < len(lines):
            current = lines[i].strip()
            # 跳过空行
            if not current:
                merged.append(current)
                i += 1
                continue
            # 如果当前行以中文字符结尾，且下一行不以标题标记或数字编号开头
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and ParserDispatcher._should_merge(current, next_line):
                    merged.append(current + next_line)
                    i += 2
                    continue
            merged.append(lines[i])
            i += 1
        return "\n".join(merged)

    @staticmethod
    def _should_merge(current: str, next_line: str) -> bool:
        """判断两行是否应该合并"""
        # 中文、日韩文字结尾，且下一行不以标题标记开头
        if re.search(r"[一-鿿぀-ゟ゠-ヿ가-힯]$", current):
            return not re.match(r"^(?:#{1,6}\s|第[一二三四五六七八九十\d]+章|第[一二三四五六七八九十\d]+节|\d+\.)", next_line)
        # 小写字母结尾
        if re.search(r"[a-z]$", current):
            return not re.match(r"^[A-Z]", next_line)
        return False

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """规范化空白字符"""
        # 将多个连续空白合并为一个
        text = re.sub(r"[ \t]+", " ", text)
        # 去除首尾空白
        text = text.strip()
        # 将三个以上连续换行压缩为两个
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    @staticmethod
    def _remove_duplicate_headers_footers(result: ParseResult) -> None:
        """去除跨页重复的页眉页脚

        规则: 如果多页的首行（或末行）完全相同，且长度较短（<100字符），
        视为重复页眉/页脚，从这些页中移除。
        """
        if len(result.pages) < 2:
            return

        # 检查首页行是否跨页重复
        first_lines = [p.text.split("\n")[0].strip() if p.text.strip() else "" for p in result.pages]
        for pattern in set(first_lines):
            if not pattern or len(pattern) > 100:
                continue
            count = sum(1 for line in first_lines if line == pattern)
            if count >= 2:
                for page in result.pages:
                    lines = page.text.split("\n")
                    if lines and lines[0].strip() == pattern:
                        lines.pop(0)
                        page.text = "\n".join(lines)
