"""输入/输出安全检查（成员6）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


INJECTION_PATTERNS = [
    r"忽略以上指令",
    r"ignore\s+(all\s+)?previous",
    r"系统提示词",
    r"system\s+prompt",
    r"你现在是",
]

LEAK_PATTERNS = [
    r"(?i)(api[_-]?key|secret_key|password)\s*[:=]\s*\S+",
    r"minio://\S+",
    r"(?i)/data/[^\s]+",
    r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*",
]


@dataclass
class SafetyResult:
    ok: bool = True
    reasons: list[str] = field(default_factory=list)
    sanitized_text: str = ""


def check_input_safety(text: str) -> SafetyResult:
    reasons: list[str] = []
    sanitized = text
    for pat in INJECTION_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            reasons.append(f"input_injection:{pat}")
            sanitized = re.sub(pat, "[已屏蔽]", sanitized, flags=re.IGNORECASE)
    # 过长异常输入
    if len(text) > 8000:
        reasons.append("input_too_long")
        sanitized = sanitized[:8000]
    return SafetyResult(ok=len(reasons) == 0, reasons=reasons, sanitized_text=sanitized)


def check_output_safety(text: str) -> SafetyResult:
    reasons: list[str] = []
    sanitized = text
    for pat in LEAK_PATTERNS:
        if re.search(pat, text):
            reasons.append(f"output_leak:{pat}")
            sanitized = re.sub(pat, "[已脱敏]", sanitized)
    if "系统提示词" in text:
        reasons.append("output_system_prompt_leak")
        sanitized = sanitized.replace("系统提示词", "[已脱敏]")
    return SafetyResult(ok=len(reasons) == 0, reasons=reasons, sanitized_text=sanitized)
