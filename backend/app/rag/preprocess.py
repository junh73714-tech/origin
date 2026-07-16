"""查询预处理：清洗、改写、意图、关键词与实体。"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field


ENTERPRISE_SYNONYMS = {
    "制度": ["规章", "规定", "办法"],
    "员工": ["职员", "人员"],
}


@dataclass
class PreprocessResult:
    original_query: str
    rewritten_query: str
    intent: str
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    timings_ms: dict[str, int] = field(default_factory=dict)
    rule_version: str = "preprocess-v1"


def basic_clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9][A-Za-z0-9\-_/]{1,}", text)
    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:20]


def extract_entities(text: str) -> list[str]:
    entities: list[str] = []
    # 编号/型号
    entities.extend(re.findall(r"[A-Z]{1,5}-\d{2,}|[A-Z]{2,}\d{2,}", text))
    # 简单地区
    for region in ("华东", "华南", "华北", "北京", "上海", "深圳", "广州"):
        if region in text:
            entities.append(region)
    # 年份
    entities.extend(re.findall(r"20\d{2}年?", text))
    # 去重
    seen: set[str] = set()
    out: list[str] = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def classify_intent(text: str, keywords: list[str], entities: list[str]) -> str:
    # 非企业知识优先判定，避免被“怎么/如何”描述性规则抢占
    if any(x in text for x in ("天气", "娱乐", "笑话", "股市行情")):
        return "refuse_or_guide"
    if any(x in text for x in ("制度", "条款", "规定", "办法")):
        return "hybrid"
    if any(re.match(r".*[A-Z]{1,5}-\d+.*", k) for k in keywords) or (
        entities and re.search(r"[A-Z]{1,5}-\d+|型号|编号", text)
    ):
        return "keyword_prefer"
    if any(x in text for x in ("是什么", "如何", "怎么", "为什么", "说明")):
        return "vector_prefer"
    if entities:
        return "keyword_prefer"
    return "hybrid"


def query_rewrite(original: str, history: list[str] | None = None) -> str:
    """
    Query Rewrite：不得删除编号、型号、地区、时间、适用人群、否定词和权限相关条件。
    """
    cleaned = basic_clean(original)
    # 多轮补全：若当前过短且历史存在，拼接上一轮关键实体
    if history and len(cleaned) < 8:
        prev = history[-1]
        ents = extract_entities(prev)
        if ents:
            cleaned = f"{cleaned}（上下文：{'、'.join(ents)}）"
    # 同义词扩展（追加，不替换关键条件）
    extras: list[str] = []
    for key, syns in ENTERPRISE_SYNONYMS.items():
        if key in cleaned:
            extras.extend(syns[:1])
    if extras:
        cleaned = f"{cleaned} {' '.join(extras)}"
    return cleaned


def preprocess(query: str, history: list[str] | None = None) -> PreprocessResult:
    t0 = time.perf_counter()
    original = basic_clean(query)
    t1 = time.perf_counter()
    rewritten = query_rewrite(original, history=history)
    t2 = time.perf_counter()
    keywords = extract_keywords(rewritten)
    entities = extract_entities(rewritten)
    intent = classify_intent(rewritten, keywords, entities)
    t3 = time.perf_counter()
    return PreprocessResult(
        original_query=original,
        rewritten_query=rewritten,
        intent=intent,
        keywords=keywords,
        entities=entities,
        timings_ms={
            "clean": int((t1 - t0) * 1000),
            "rewrite": int((t2 - t1) * 1000),
            "extract": int((t3 - t2) * 1000),
        },
    )
