"""
文档切分服务

提供多种切分策略将解析后的文档切分为语义完整的 Chunk。

支持的切分策略:
1. 标题层级切分 -- 按H1/H2/H3等标题层级切分
2. 章节切分 -- 按章节边界切分
3. 段落切分 -- 按自然段落切分
4. 条款切分 -- 合同/法规按条款编号切分
5. Token上限 -- 单Chunk不超过配置上限
6. 相邻重叠 -- 配置化重叠窗口避免语义断裂
7. 表格切分 -- 表格独立为Chunk或按行切分
8. 长段落二次切分 -- 超过Token上限的段落二次切分

成员5主责：文档切分策略实现
"""
import re
import os
import math
from dataclasses import dataclass, field

from app.services.parsing.base import ParseResult, PageElement, TableElement


# ---------------------------------------------------------------------------
# Chunk 输出数据结构
# ---------------------------------------------------------------------------

@dataclass
class ChunkData:
    """单个Chunk的数据结构"""
    raw_text: str                          # 原始文本
    clean_text: str                        # 清洗后文本
    title_path: str | None = None          # 标题路径 (用 > 分隔层级)
    page_start: int | None = None          # 起始页码
    page_end: int | None = None            # 结束页码
    source_offset: int = 0                 # 原文偏移位置
    token_count: int = 0                   # Token计数
    chunk_type: str = "paragraph"          # Chunk类型
    chunk_no: int = 0                      # 切分序号（后期分配）
    metadata: dict = field(default_factory=dict)  # 额外元数据


# ---------------------------------------------------------------------------
# Token 估算工具
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """
    估算文本的Token数量

    使用简单的字符比例估算（中文约1.5字符/token，英文约4字符/token）。
    生产环境应使用 tiktoken 精确计算。
    """
    if not text:
        return 0

    chinese_chars = len(re.findall(r"[一-鿿]", text))
    other_chars = len(text) - chinese_chars
    # 中文字符占比更高（每token约1.5个中文字符）
    chinese_tokens = math.ceil(chinese_chars / 1.5)
    # 英文/数字/标点（每token约4个字符）
    other_tokens = math.ceil(other_chars / 4.0)
    return chinese_tokens + other_tokens


# ---------------------------------------------------------------------------
# 文档切分器
# ---------------------------------------------------------------------------

class DocumentChunker:
    """
    文档切分器

    根据解析结果和配置参数，将文档切分为语义完整的Chunk列表。
    """

    def __init__(
        self,
        max_tokens: int = 500,        # 单Chunk最大Token数
        overlap_tokens: int = 50,     # 相邻Chunk重叠Token数
        min_chunk_tokens: int = 20,   # 最小Chunk Token数（小于此值的合并到前一个）
        split_tables: bool = True,    # 表格是否独立为Chunk
        include_headers_in_chunks: bool = True,  # Chunk中是否包含标题路径
    ):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.split_tables = split_tables
        self.include_headers_in_chunks = include_headers_in_chunks

    # -------------------------------------------------------------------------
    # 主入口
    # -------------------------------------------------------------------------

    def chunk(self, parse_result: ParseResult) -> list[ChunkData]:
        """
        对解析结果执行切分

        处理流程:
        1. 从解析结果中提取所有内容单元
        2. 按策略切分为初步Chunk
        3. 处理Token上限（二次切分超限Chunk）
        4. 合并过小的Chunk
        5. 添加重叠窗口
        6. 分配序号和元数据

        Args:
            parse_result: 文档解析结果

        Returns:
            list[ChunkData]: 切分后的Chunk列表
        """
        raw_chunks = self._extract_chunks(parse_result)
        sized_chunks = self._apply_token_limit(raw_chunks)
        merged_chunks = self._merge_small_chunks(sized_chunks)
        final_chunks = self._apply_overlap(merged_chunks)
        numbered_chunks = self._assign_chunk_numbers(final_chunks, parse_result)

        return numbered_chunks

    # -------------------------------------------------------------------------
    # 第一步: 从解析结果提取内容单元
    # -------------------------------------------------------------------------

    def _extract_chunks(self, result: ParseResult) -> list[ChunkData]:
        """
        从解析结果提取初步Chunk

        根据文档类型采用不同的切分策略。
        """
        # 构建当前标题路径
        current_title_path: list[str] = []
        chunks: list[ChunkData] = []

        for page in result.pages:
            # 更新标题路径
            for heading in page.headings:
                level = heading.get("level", 1)
                title_text = heading.get("text", "")
                # 根据层级更新标题路径
                if level <= len(current_title_path):
                    current_title_path = current_title_path[: level - 1]
                current_title_path.append(title_text)

            title_path_str = " > ".join(current_title_path) if current_title_path else None

            # 处理表格（如果开启表格独立切分）
            if self.split_tables:
                for table in page.tables:
                    table_text = self._table_to_text(table)
                    chunks.append(ChunkData(
                        raw_text=table_text,
                        clean_text=table_text,
                        title_path=title_path_str,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        source_offset=page.raw_offset,
                        chunk_type="table",
                        metadata={"headers": table.headers, "row_count": len(table.rows)},
                    ))

            # 处理段落
            if page.paragraphs:
                for para in page.paragraphs:
                    chunks.append(ChunkData(
                        raw_text=para,
                        clean_text=para,
                        title_path=title_path_str,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        source_offset=page.raw_offset,
                        chunk_type="paragraph",
                    ))
            else:
                # 无段落信息时，尝试按句子/换行切分
                text = page.text
                if text:
                    # 按双换行或单换行切分
                    sections = self._split_by_clauses(text)
                    for section in sections:
                        if section.strip():
                            chunks.append(ChunkData(
                                raw_text=section,
                                clean_text=section,
                                title_path=title_path_str,
                                page_start=page.page_number,
                                page_end=page.page_number,
                                source_offset=page.raw_offset,
                                chunk_type="section",
                            ))

        return chunks

    # -------------------------------------------------------------------------
    # 第二步: Token上限处理
    # -------------------------------------------------------------------------

    def _apply_token_limit(self, chunks: list[ChunkData]) -> list[ChunkData]:
        """
        对超过Token上限的Chunk进行二次切分

        策略：
        - 段落类型：按句子边界切分
        - 表格类型：按行切分
        - 其他类型：按字符切分并保留句子完整性
        """
        result: list[ChunkData] = []

        for chunk in chunks:
            tokens = estimate_tokens(chunk.clean_text)
            if tokens <= self.max_tokens:
                result.append(chunk)
                continue

            # 需要二次切分
            if chunk.chunk_type == "table":
                # 表格按行切分
                sub_chunks = self._split_table_by_rows(chunk)
            else:
                # 按句子边界切分
                sub_chunks = self._split_by_sentences(chunk)

            result.extend(sub_chunks)

        return result

    def _split_by_sentences(self, chunk: ChunkData) -> list[ChunkData]:
        """按句子边界切分长段落"""
        # 按中文和英文句子分隔符拆分
        sentences = re.split(r"(?<=[。！？.!?\n])\s*", chunk.clean_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            # 无法按句子拆分，按字符长度强行切分
            return self._split_by_chars(chunk)

        sub_chunks: list[ChunkData] = []
        current_text = ""
        current_tokens = 0

        for sentence in sentences:
            sent_tokens = estimate_tokens(sentence)
            if current_tokens + sent_tokens > self.max_tokens and current_text:
                sub_chunks.append(self._make_sub_chunk(chunk, current_text))
                current_text = sentence
                current_tokens = sent_tokens
            else:
                if current_text:
                    current_text += " "
                current_text += sentence
                current_tokens += sent_tokens

        if current_text:
            sub_chunks.append(self._make_sub_chunk(chunk, current_text))

        return sub_chunks

    def _split_by_chars(self, chunk: ChunkData) -> list[ChunkData]:
        """按字符长度强行切分（最后手段）"""
        text = chunk.clean_text
        # 估算每个Chunk最多容纳的字符数
        chars_per_chunk = self.max_tokens * 2  # 粗略估算

        sub_chunks: list[ChunkData] = []
        for i in range(0, len(text), chars_per_chunk):
            segment = text[i: i + chars_per_chunk]
            sub_chunks.append(self._make_sub_chunk(chunk, segment))
        return sub_chunks

    def _split_table_by_rows(self, chunk: ChunkData) -> list[ChunkData]:
        """按行切分大表格"""
        headers = chunk.metadata.get("headers", [])
        row_count = chunk.metadata.get("row_count", 0)

        if row_count == 0 or not headers:
            return [chunk]

        # 每批次最多容纳的行数（考虑表头）
        header_text = " | ".join(headers)
        header_tokens = estimate_tokens(header_text)
        rows_per_chunk = max(1, (self.max_tokens - header_tokens) // 10)

        lines = chunk.clean_text.split("\n")
        sub_chunks: list[ChunkData] = []
        current_rows: list[str] = [header_text]

        for line in lines[1:]:  # 跳过表头行（第一个元素）
            current_rows.append(line)
            if len(current_rows) - 1 >= rows_per_chunk:  # -1 因为包含表头
                sub_text = "\n".join(current_rows)
                sub_chunks.append(self._make_sub_chunk(chunk, sub_text))
                current_rows = [header_text]

        if len(current_rows) > 1:
            sub_text = "\n".join(current_rows)
            sub_chunks.append(self._make_sub_chunk(chunk, sub_text))

        return sub_chunks or [chunk]

    def _make_sub_chunk(self, original: ChunkData, text: str) -> ChunkData:
        """从原始Chunk创建子Chunk"""
        return ChunkData(
            raw_text=text,
            clean_text=text,
            title_path=original.title_path,
            page_start=original.page_start,
            page_end=original.page_end,
            source_offset=original.source_offset,
            chunk_type=original.chunk_type,
            metadata=dict(original.metadata),
        )

    # -------------------------------------------------------------------------
    # 第三步: 合并过小Chunk
    # -------------------------------------------------------------------------

    def _merge_small_chunks(self, chunks: list[ChunkData]) -> list[ChunkData]:
        """
        合并过小的Chunk到前一个Chunk

        小于 min_chunk_tokens 且与前一个Chunk同页/同类型的Chunk，
        合并到前一个Chunk中。
        """
        if not chunks:
            return chunks

        result: list[ChunkData] = [chunks[0]]

        for chunk in chunks[1:]:
            prev = result[-1]
            chunk_tokens = estimate_tokens(chunk.clean_text)
            prev_tokens = estimate_tokens(prev.clean_text)

            # 判断是否应该合并（任一Chunk过小且合并后不超限）
            should_merge = (
                (chunk_tokens < self.min_chunk_tokens or prev_tokens < self.min_chunk_tokens)
                and prev.chunk_type == chunk.chunk_type  # 同类型
                and prev_tokens + chunk_tokens <= self.max_tokens
            )

            if should_merge:
                # 合并到前一个Chunk
                prev.raw_text += "\n" + chunk.raw_text
                prev.clean_text += "\n" + chunk.clean_text
                prev.page_end = chunk.page_end
                if chunk.metadata:
                    prev.metadata.update(chunk.metadata)
            else:
                result.append(chunk)

        return result

    # -------------------------------------------------------------------------
    # 第四步: 重叠窗口
    # -------------------------------------------------------------------------

    def _apply_overlap(self, chunks: list[ChunkData]) -> list[ChunkData]:
        """
        为相邻Chunk添加重叠文本

        从每个后续Chunk中取前 overlap_tokens 个Token的文本，
        追加到前一个Chunk的末尾。

        这避免了在Chunk边界处丢失上下文语义。
        """
        if not chunks or self.overlap_tokens <= 0:
            return chunks

        for i in range(len(chunks) - 1):
            current = chunks[i]
            next_chunk = chunks[i + 1]

            # 从下一个Chunk的头部取重叠文本
            overlap_text = self._extract_head_tokens(
                next_chunk.clean_text, self.overlap_tokens
            )
            if overlap_text:
                current.clean_text += "\n" + overlap_text
                current.raw_text += "\n" + overlap_text

        return chunks

    def _extract_head_tokens(self, text: str, token_count: int) -> str:
        """从文本头部提取指定数量的Token"""
        if not text:
            return ""

        # 简单实现：取前 token_count * 2 个字符（粗略估算）
        chars_to_take = min(len(text), token_count * 2)
        # 尽量在句子边界截断
        segment = text[:chars_to_take]
        # 找到最后一个句子结束符
        for sep in ["。", "！", "？", ".", "!", "?", "\n"]:
            last_idx = segment.rfind(sep)
            if last_idx > chars_to_take // 2:
                return segment[: last_idx + 1]

        return segment

    # -------------------------------------------------------------------------
    # 第五步: 分配序号
    # -------------------------------------------------------------------------

    def _assign_chunk_numbers(
        self, chunks: list[ChunkData], result: ParseResult
    ) -> list[ChunkData]:
        """为每个Chunk分配序号和计算Token计数"""
        for i, chunk in enumerate(chunks, 1):
            chunk.chunk_no = i
            chunk.token_count = estimate_tokens(chunk.clean_text)
        return chunks

    # -------------------------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------------------------

    @staticmethod
    def _table_to_text(table: TableElement) -> str:
        """将表格转换为可检索文本"""
        lines = []
        if table.headers:
            lines.append(" | ".join(table.headers))
        for row in table.rows:
            lines.append(" | ".join(row))
        return "\n".join(lines)

    @staticmethod
    def _split_by_clauses(text: str) -> list[str]:
        """
        按条款编号切分文本

        匹配模式:
        - "第X条" / "第X款"
        - "第X章" / "第X节"
        - 数字编号 (1. / 1.1 / (1) / ①)
        """
        # 条款分隔正则
        clause_pattern = re.compile(
            r"(?=(?:^|\n)\s*(?:第[一二三四五六七八九十\d]+[条款章节目]|"
            r"\d+[\.\)、]|\([一二三四五六七八九十\d]+\)|"
            r"[①②③④⑤⑥⑦⑧⑨⑩]))"
        )

        parts = clause_pattern.split(text)
        return [p.strip() for p in parts if p.strip()]
