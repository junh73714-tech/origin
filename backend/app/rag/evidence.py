"""证据覆盖度评估。"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.retrieval.types import RetrievalHit


CRITICAL_KEYS = ("地区", "时间", "适用人群", "岗位", "制度", "编号", "型号", "不", "非", "不得")


@dataclass
class EvidenceAssessment:
    coverage_score: float
    covered: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    decision: str = "generate"  # generate | supplement | ask_user | refuse | conflict
    rule_version: str = "evidence-v1"


def extract_critical_conditions(query: str) -> list[str]:
    found: list[str] = []
    for key in CRITICAL_KEYS:
        if key in query:
            found.append(key)
    # 抽取类似编号
    import re

    found.extend(re.findall(r"[A-Z]{1,5}-\d{2,}", query))
    for region in ("华东", "华南", "华北", "北京", "上海", "深圳"):
        if region in query and region not in found:
            found.append(region)
    # 去重
    out: list[str] = []
    seen: set[str] = set()
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def assess_evidence(query: str, candidates: list[RetrievalHit]) -> EvidenceAssessment:
    conditions = extract_critical_conditions(query)
    if not candidates:
        return EvidenceAssessment(
            coverage_score=0.0,
            covered=[],
            missing=conditions or ["有效证据"],
            decision="refuse",
        )
    blob = " ".join((c.text_preview or "") + " " + (c.title_path or "") for c in candidates)
    covered: list[str] = []
    missing: list[str] = []
    for cond in conditions:
        if cond in blob:
            covered.append(cond)
        else:
            missing.append(cond)

    # 简单冲突：同时出现互相矛盾的否定
    conflicts: list[str] = []
    if "不得" in blob and "应当" in blob and "不得" in query:
        conflicts.append("义务表述可能冲突")

    if not conditions:
        score = 0.7 if candidates else 0.0
        decision = "generate" if score >= 0.5 else "refuse"
    else:
        score = len(covered) / max(1, len(conditions))
        if conflicts:
            decision = "conflict"
        elif score >= 0.999:
            decision = "generate"
        elif score >= 0.5:
            decision = "supplement"
        elif score > 0:
            decision = "ask_user"
        else:
            decision = "refuse"

    return EvidenceAssessment(
        coverage_score=score,
        covered=covered,
        missing=missing,
        conflicts=conflicts,
        decision=decision,
    )
