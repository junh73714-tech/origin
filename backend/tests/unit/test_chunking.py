"""
文档切分服务单元测试

测试所有切分策略: 段落切分、标题路径、Token限制、重叠窗口、合并、表格切分、条款切分。
"""
import pytest
import math

from app.services.chunking import (
    ChunkData,
    DocumentChunker,
    estimate_tokens,
)
from app.services.parsing.base import (
    ParseResult,
    PageElement,
    TableElement,
    ParseQuality,
)


# =============================================================================
# Token估算测试
# =============================================================================

class TestTokenEstimation:

    def test_estimate_chinese(self):
        """测试中文Token估算"""
        text = "这是一个测试文档"
        tokens = estimate_tokens(text)
        assert tokens > 0
        # 8个中文字符 / 1.5 = ~6 tokens
        assert 4 <= tokens <= 10

    def test_estimate_english(self):
        """测试英文Token估算"""
        text = "This is a test document for token counting"
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_estimate_mixed(self):
        """测试中英混合Token估算"""
        text = "这是test测试document文档"
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_estimate_empty(self):
        """测试空文本Token估算"""
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0


# =============================================================================
# 段落切分测试
# =============================================================================

class TestParagraphChunking:

    def _make_result_with_paragraphs(self, paragraphs: list[str]) -> ParseResult:
        """创建带段落的测试ParseResult"""
        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        page.paragraphs = paragraphs
        page.text = "\n\n".join(paragraphs)
        result.total_chars = len(page.text)
        result.pages.append(page)
        return result

    def test_basic_paragraph_chunking(self):
        """测试基本段落切分"""
        result = self._make_result_with_paragraphs([
            "第一段内容。这是一个测试段落。",
            "第二段内容。包含更多测试数据。",
            "第三段内容。最后一段。",
        ])

        # 使用 min_chunk_tokens=0 避免小段落被合并
        chunker = DocumentChunker(min_chunk_tokens=0)
        chunks = chunker.chunk(result)

        assert len(chunks) == 3
        assert chunks[0].chunk_no == 1
        assert chunks[1].chunk_no == 2
        assert chunks[2].chunk_no == 3

    def test_chunk_metadata(self):
        """测试Chunk元数据"""
        result = self._make_result_with_paragraphs([
            "测试内容段落。",
        ])

        chunker = DocumentChunker()
        chunks = chunker.chunk(result)

        assert len(chunks) == 1
        ch = chunks[0]
        assert ch.chunk_type == "paragraph"
        assert ch.page_start == 1
        assert ch.token_count > 0
        assert ch.clean_text is not None

    def test_chunk_no_monotonic(self):
        """测试Chunk序号递增"""
        result = self._make_result_with_paragraphs([
            f"段落{i}" for i in range(10)
        ])

        chunker = DocumentChunker()
        chunks = chunker.chunk(result)

        # 验证序号递增
        for i, ch in enumerate(chunks, 1):
            assert ch.chunk_no == i


# =============================================================================
# 标题路径测试
# =============================================================================

class TestTitlePathChunking:

    def test_title_path_in_chunks(self):
        """测试标题路径在Chunk中正确传递"""
        result = ParseResult(file_type="html", total_pages=1)
        page = PageElement(page_number=1)
        page.headings = [
            {"level": 1, "text": "第一章 概述", "position": 0},
            {"level": 2, "text": "第一节 背景", "position": 10},
        ]
        page.paragraphs = [
            "这是第一章第一节的内容。",
            "继续第一节的内容。",
        ]
        page.text = "第一章 概述\n第一节 背景\n这是第一章第一节的内容。\n继续第一节的内容。"
        result.total_chars = len(page.text)
        result.pages.append(page)

        chunker = DocumentChunker()
        chunks = chunker.chunk(result)

        # 验证标题路径
        for ch in chunks:
            assert "第一章 概述" in (ch.title_path or "")
            assert "第一节 背景" in (ch.title_path or "")


# =============================================================================
# Token限制测试
# =============================================================================

class TestTokenLimit:

    def test_long_paragraph_split(self):
        """测试长段落被二次切分"""
        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        # 创建超长段落
        long_text = "这是一个很长的句子。" * 200  # 约2000字符
        page.paragraphs = [long_text]
        page.text = long_text
        result.total_chars = len(page.text)
        result.pages.append(page)

        chunker = DocumentChunker(max_tokens=200, overlap_tokens=0)
        chunks = chunker.chunk(result)

        # 长段落应被切分为多个Chunk
        assert len(chunks) > 1

    def test_short_paragraphs_preserved(self):
        """测试短段落不被切分"""
        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        page.paragraphs = [
            "短段落一。",
            "短段落二。",
            "短段落三。",
        ]
        page.text = "\n\n".join(page.paragraphs)
        result.total_chars = len(page.text)
        result.pages.append(page)

        # min_chunk_tokens=0 确保短段落不被合并
        chunker = DocumentChunker(max_tokens=500, min_chunk_tokens=0)
        chunks = chunker.chunk(result)

        # 短段落应保持完整
        assert len(chunks) == 3

    def test_token_count_after_chunking(self):
        """测试每个Chunk的Token计数不超过限制"""
        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        page.paragraphs = [
            f"段落内容{i}。" for i in range(20)
        ]
        page.text = "\n\n".join(page.paragraphs)
        result.total_chars = len(page.text)
        result.pages.append(page)

        max_tokens = 300
        chunker = DocumentChunker(max_tokens=max_tokens, overlap_tokens=0,
                                   min_chunk_tokens=0)
        chunks = chunker.chunk(result)

        for ch in chunks:
            assert ch.token_count <= max_tokens, (
                f"Chunk {ch.chunk_no} token_count={ch.token_count} > {max_tokens}"
            )


# =============================================================================
# 重叠窗口测试
# =============================================================================

class TestOverlapWindow:

    def test_overlap_applied(self):
        """测试重叠窗口被正确添加"""
        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        page.paragraphs = [
            "这是第一个段落的完整内容。包含一些关键信息如项目名称和日期。",
            "这是第二个段落的完整内容。引用了前面提到的项目名称和日期。",
        ]
        page.text = "\n\n".join(page.paragraphs)
        result.total_chars = len(page.text)
        result.pages.append(page)

        chunker = DocumentChunker(max_tokens=500, overlap_tokens=30)
        chunks = chunker.chunk(result)

        # 第一个Chunk应该包含第二个Chunk的部分重叠内容
        if len(chunks) >= 2:
            # 验证第一个Chunk的clean_text比raw_text更长（包含重叠）
            assert len(chunks[0].clean_text) >= len(chunks[0].raw_text)


# =============================================================================
# 小Chunk合并测试
# =============================================================================

class TestMergeSmallChunks:

    def test_small_chunks_merged(self):
        """测试过小Chunk被合并"""
        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        page.paragraphs = [
            "这是正常大小的段落，包含足够的文本内容来超越最小Token限制。",
            "短。",
            "另一个正常段落，同样包含足够的文本内容。",
        ]
        page.text = "\n\n".join(page.paragraphs)
        result.total_chars = len(page.text)
        result.pages.append(page)

        chunker = DocumentChunker(min_chunk_tokens=10)
        chunks = chunker.chunk(result)

        # "短。" 应该被合并（小于10 tokens）
        # 结果应该少于3个Chunk
        assert len(chunks) < 3


# =============================================================================
# 表格切分测试
# =============================================================================

class TestTableChunking:

    def test_table_split_as_chunk(self):
        """测试表格独立为Chunk"""
        result = ParseResult(file_type="pdf", total_pages=1)
        page = PageElement(page_number=1)
        page.paragraphs = ["表格前的段落内容。"]
        page.tables.append(TableElement(
            headers=["姓名", "部门", "职位"],
            rows=[["张三", "技术部", "工程师"], ["李四", "人事部", "经理"]],
            page=1,
        ))
        page.text = "表格前的段落内容。\n姓名 | 部门 | 职位\n张三 | 技术部 | 工程师\n李四 | 人事部 | 经理"
        result.total_chars = len(page.text)
        result.pages.append(page)

        chunker = DocumentChunker(split_tables=True)
        chunks = chunker.chunk(result)

        # 应包含段落Chunk和表格Chunk
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) == 1
        assert "张三" in table_chunks[0].clean_text
        assert table_chunks[0].metadata.get("headers") == ["姓名", "部门", "职位"]


# =============================================================================
# 条款切分测试
# =============================================================================

class TestClauseChunking:

    def test_clause_split(self):
        """测试条款切分"""
        from app.services.chunking import DocumentChunker

        text = """第一条 总则
本制度适用于公司全体员工。

第二条 考勤管理
员工应按时上下班，不得迟到早退。

第三条 请假制度
员工请假应提前申请，经批准后方可休假。"""

        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        page.text = text
        result.total_chars = len(text)
        result.pages.append(page)

        # min_chunk_tokens=0 避免条款段落因过短被合并
        chunker = DocumentChunker(min_chunk_tokens=0)
        chunks = chunker.chunk(result)

        # 每一条被切分为独立Chunk
        assert len(chunks) == 3
        assert "第一条" in chunks[0].clean_text
        assert "第二条" in chunks[1].clean_text
        assert "第三条" in chunks[2].clean_text

    def test_clause_split_helper(self):
        """测试条款切分辅助函数"""
        from app.services.chunking import DocumentChunker

        text = """第一条 定义
术语解释。

第二条 范围
适用范围说明。"""

        parts = DocumentChunker._split_by_clauses(text)
        assert len(parts) == 2
        assert "第一条" in parts[0]
        assert "第二条" in parts[1]


# =============================================================================
# 边界情况测试
# =============================================================================

class TestEdgeCases:

    def test_empty_result(self):
        """测试空解析结果"""
        result = ParseResult(file_type="txt")
        chunker = DocumentChunker()
        chunks = chunker.chunk(result)
        assert len(chunks) == 0

    def test_single_word_paragraph(self):
        """测试单字段落"""
        result = ParseResult(file_type="txt", total_pages=1)
        page = PageElement(page_number=1)
        page.paragraphs = ["A", "正常段落内容。"]
        page.text = "A\n\n正常段落内容。"
        result.total_chars = len(page.text)
        result.pages.append(page)

        chunker = DocumentChunker(min_chunk_tokens=5)
        chunks = chunker.chunk(result)

        # 单字段落应被合并
        assert len(chunks) < 2

    def test_preserve_page_info(self):
        """测试跨页Chunk的页码信息"""
        result = ParseResult(file_type="pdf", total_pages=2)
        p1 = PageElement(page_number=1)
        p1.paragraphs = ["第一页的段落。"]
        p1.text = "第一页的段落。"
        p2 = PageElement(page_number=2)
        p2.paragraphs = ["第二页的段落。"]
        p2.text = "第二页的段落。"
        result.total_chars = len(p1.text) + len(p2.text)
        result.pages = [p1, p2]

        chunker = DocumentChunker(min_chunk_tokens=0)
        chunks = chunker.chunk(result)

        assert len(chunks) == 2
        assert chunks[0].page_start == 1
        assert chunks[1].page_start == 2
