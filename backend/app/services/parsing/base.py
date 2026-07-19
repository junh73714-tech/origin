"""
文档解析器基类和结果类型

定义统一的解析结果数据结构和解析器接口。
所有格式的解析器必须继承 BaseParser 并实现 parse 方法。

成员5主责：解析结果标准格式定义
"""
import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import BinaryIO


class ParseQuality(str, Enum):
    """解析质量等级"""
    GOOD = "good"        # 解析成功，质量良好
    WARNING = "warning"  # 解析成功，存在可修复的警告
    DEGRADED = "degraded"  # 部分解析，存在数据丢失
    ERROR = "error"      # 解析失败


@dataclass
class ParseWarning:
    """解析警告信息"""
    code: str                    # 警告类型代码
    message: str                 # 警告描述
    page: int | None = None      # 所在页码
    position: int | None = None  # 原文偏移位置
    detail: str | None = None    # 详细信息


@dataclass
class TableElement:
    """表格元素

    解析后的表格数据，保留表头和行列结构。
    """
    headers: list[str] = field(default_factory=list)  # 表头列表
    rows: list[list[str]] = field(default_factory=list)  # 数据行列表
    page: int | None = None       # 所在页码
    caption: str | None = None    # 表格标题
    position: int | None = None   # 原文偏移位置


@dataclass
class PageElement:
    """页面内容元素

    记录一页内的所有结构信息。
    """
    page_number: int = 1
    text: str = ""                  # 页面完整文本
    paragraphs: list[str] = field(default_factory=list)  # 段落列表
    headings: list[dict] = field(default_factory=list)   # 标题列表 [{level, text, position}]
    lists: list[str] = field(default_factory=list)       # 列表项文本
    tables: list[TableElement] = field(default_factory=list)  # 表格列表
    raw_offset: int = 0             # 本页在原文中的起始偏移


@dataclass
class ParseResult:
    """
    统一的文档解析结果

    所有格式解析器必须返回此结构。
    """
    file_type: str                        # 文件类型: pdf/docx/txt/md/html
    total_pages: int = 0                  # 总页数（非分页格式如txt/md/html为1）
    total_chars: int = 0                  # 总字符数
    pages: list[PageElement] = field(default_factory=list)  # 页面列表
    tables: list[TableElement] = field(default_factory=list)  # 全局表格列表
    quality: ParseQuality = ParseQuality.GOOD  # 解析质量
    warnings: list[ParseWarning] = field(default_factory=list)  # 警告列表
    error_message: str | None = None      # 错误信息（质量ERROR时）
    error_type: str | None = None         # 错误类型
    metadata: dict = field(default_factory=dict)  # 解析器元数据

    @property
    def full_text(self) -> str:
        """获取文档的完整文本"""
        return "\n".join(page.text for page in self.pages)

    @property
    def has_tables(self) -> bool:
        """是否包含表格"""
        return len(self.tables) > 0 or any(len(p.tables) > 0 for p in self.pages)

    @property
    def has_errors(self) -> bool:
        """是否有严重错误"""
        return self.quality == ParseQuality.ERROR

    @property
    def heading_count(self) -> int:
        """标题总数"""
        return sum(len(p.headings) for p in self.pages)


class BaseParser(abc.ABC):
    """文档解析器抽象基类

    所有格式解析器必须实现:
    - parse(): 从字节数据解析文档
    - parse_stream(): 从文件流解析文档
    - supported_format: 支持的文件格式标识
    """

    @property
    @abc.abstractmethod
    def supported_format(self) -> str:
        """返回支持的文件格式标识: pdf/docx/txt/md/html"""
        ...

    @abc.abstractmethod
    def parse(self, data: bytes, filename: str = "") -> ParseResult:
        """
        解析文档字节数据

        Args:
            data: 文件二进制数据
            filename: 原始文件名（用于判断格式和日志）

        Returns:
            ParseResult: 统一的解析结果

        Raises:
            DocumentParsingError: 解析不可恢复时
        """
        ...

    @abc.abstractmethod
    def parse_stream(self, stream: BinaryIO, filename: str = "") -> ParseResult:
        """
        流式解析文档（适用于大文件）

        Args:
            stream: 文件流对象
            filename: 原始文件名

        Returns:
            ParseResult: 统一的解析结果
        """
        ...

    def _make_result(self, file_type: str) -> ParseResult:
        """创建初始解析结果"""
        return ParseResult(file_type=file_type)
