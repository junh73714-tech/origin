"""
LLMProvider 抽象。

真实 LLM 绑定列为硬阻塞：完成 provider-agnostic 核心与契约一致测试替身。
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMGenerateResult(BaseModel):
    """结构化生成结果。"""

    answer: str
    answer_type: str = "rag"
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    evidence_status: str = "unknown"
    refusal_reason: str | None = None
    model_name: str = ""
    model_version: str = ""
    prompt_version: str = ""
    duration_ms: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)
    is_mock: bool = False
    raw_text: str = ""


class LLMProvider(Protocol):
    model_name: str
    model_version: str

    def generate(self, system_prompt: str, user_prompt: str) -> LLMGenerateResult: ...


class MockLLMProvider:
    """测试替身：基于证据覆盖生成结构化答案，is_mock=True。"""

    def __init__(
        self,
        model_name: str | None = None,
        model_version: str = "mock-v1",
        prompt_version: str = "qa-prompt-v1",
    ):
        self.model_name = model_name or settings.llm.model
        self.model_version = model_version
        self.prompt_version = prompt_version
        self.is_bound = False

    def generate(self, system_prompt: str, user_prompt: str) -> LLMGenerateResult:
        del system_prompt
        started = time.perf_counter()
        # 从 user_prompt 中提取 citation 标记
        citation_ids = re.findall(r"\[citation:([^\]]+)\]", user_prompt)
        evidence_block = ""
        if "证据：" in user_prompt:
            evidence_block = user_prompt.split("证据：", 1)[-1]
        if "拒答" in user_prompt or "无有效证据" in user_prompt or not evidence_block.strip():
            result = LLMGenerateResult(
                answer="当前证据不足，无法给出可靠结论，请补充问题条件或更换知识范围。",
                answer_type="refusal",
                citations=[],
                confidence=0.0,
                evidence_status="insufficient",
                refusal_reason="证据不足",
                model_name=self.model_name,
                model_version=self.model_version,
                prompt_version=self.prompt_version,
                is_mock=True,
            )
        else:
            snippet = evidence_block.strip().splitlines()[0][:200]
            result = LLMGenerateResult(
                answer=f"根据提供的有效上下文：{snippet}",
                answer_type="rag",
                citations=[{"citation_id": cid} for cid in citation_ids],
                confidence=0.6 if citation_ids else 0.3,
                evidence_status="partial" if citation_ids else "weak",
                refusal_reason=None,
                model_name=self.model_name,
                model_version=self.model_version,
                prompt_version=self.prompt_version,
                is_mock=True,
                raw_text="",
            )
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.token_usage = {
            "prompt_tokens": max(1, len(user_prompt) // 4),
            "completion_tokens": max(1, len(result.answer) // 4),
        }
        result.raw_text = json.dumps(result.model_dump(), ensure_ascii=False)
        logger.info(
            "llm_generate_done",
            model=self.model_name,
            is_mock=True,
            answer_type=result.answer_type,
            duration_ms=result.duration_ms,
        )
        return result


def get_llm_provider() -> LLMProvider:
    """返回 LLMProvider；真实服务未绑定前使用 Mock。"""
    return MockLLMProvider()
