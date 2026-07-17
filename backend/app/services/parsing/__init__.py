"""
文档解析模块

支持格式: PDF / DOCX / TXT / Markdown / HTML

成员5主责：文档解析和OCR Provider接口
"""
from app.services.parsing.base import (
    ParseResult,
    PageElement,
    TableElement,
    ParseWarning,
    ParseQuality,
    BaseParser,
)
from app.services.parsing.dispatcher import ParserDispatcher, get_parser

__all__ = [
    "ParseResult",
    "PageElement",
    "TableElement",
    "ParseWarning",
    "ParseQuality",
    "BaseParser",
    "ParserDispatcher",
    "get_parser",
]
