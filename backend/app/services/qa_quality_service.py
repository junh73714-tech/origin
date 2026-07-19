"""
质量检查服务（成员7）
自动质量检查，辅助审核但不替代人工审核
至少10项检查项
"""
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.qa import CandidateQA, QAQualityCheck, StandardQA

logger = get_logger(__name__)

# 敏感信息正则模式
SENSITIVE_PATTERNS = [
    (r"\b\d{15,19}\b", "银行卡号"),
    (r"\b\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", "身份证号"),
    (r"\b1[3-9]\d{9}\b", "手机号"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "邮箱地址"),
]

# 绝对化表述模式
ABSOLUTE_PATTERNS = [
    r"绝对是", r"肯定是", r"一定是", r"绝对是", r"毫无疑问",
    r"百分百", r"100%", r"绝无", r"绝不", r"永远不",
    r"绝对不", r"必然", r"必定", r"保证", r"肯定",
]


class QAQualityCheckService:
    """质量检查服务"""

    CHECKER_VERSION = "1.0.0"

    # 检查项定义
    CHECKS = [
        {
            "name": "source_support",
            "label": "答案是否有来源支持",
            "is_blocking": True,
        },
        {
            "name": "beyond_source",
            "label": "是否超出原文范围",
            "is_blocking": True,
        },
        {
            "name": "qa_match",
            "label": "问题和答案是否匹配",
            "is_blocking": True,
        },
        {
            "name": "missing_conditions",
            "label": "是否缺少时间、地区、岗位等条件",
            "is_blocking": False,
        },
        {
            "name": "duplicate_check",
            "label": "是否与已有问答重复",
            "is_blocking": True,
        },
        {
            "name": "sensitive_info",
            "label": "是否包含敏感信息",
            "is_blocking": True,
        },
        {
            "name": "scope_expansion",
            "label": "是否扩大权限范围",
            "is_blocking": True,
        },
        {
            "name": "source_valid",
            "label": "来源文档是否有效",
            "is_blocking": True,
        },
        {
            "name": "source_version_current",
            "label": "来源版本是否当前",
            "is_blocking": False,
        },
        {
            "name": "absolute_claims",
            "label": "是否使用绝对化但无依据的表述",
            "is_blocking": False,
        },
        {
            "name": "answer_completeness",
            "label": "答案完整性检查",
            "is_blocking": False,
        },
        {
            "name": "scope_reasonableness",
            "label": "适用范围合理性检查",
            "is_blocking": False,
        },
    ]

    async def run_all_checks(
        self,
        db: AsyncSession,
        qa: StandardQA,
        candidate_qa_id: str | None = None,
    ) -> list[QAQualityCheck]:
        """运行所有质量检查"""
        results: list[QAQualityCheck] = []
        now = datetime.now(timezone.utc)

        for check_def in self.CHECKS:
            check_name = check_def["name"]
            check_method = getattr(self, f"_check_{check_name}", None)

            if check_method is None:
                continue

            try:
                passed, score, detail = await check_method(db, qa)
            except Exception as e:
                logger.error(
                    "quality_check_error",
                    check_name=check_name,
                    qa_id=qa.id,
                    error=str(e),
                )
                passed = False
                score = 0.0
                detail = f"检查执行异常: {str(e)}"

            quality_check = QAQualityCheck(
                qa_id=qa.id,
                candidate_qa_id=candidate_qa_id,
                check_name=check_name,
                check_result=passed,
                check_score=score,
                check_detail=detail,
                is_blocking=check_def["is_blocking"],
                checked_at=now,
                checker_version=self.CHECKER_VERSION,
                tenant_id=qa.tenant_id,
                created_by="system",
            )
            db.add(quality_check)
            results.append(quality_check)

        await db.flush()
        return results

    async def get_check_summary(
        self,
        db: AsyncSession,
        qa_id: str,
    ) -> dict[str, Any]:
        """获取质量检查汇总"""
        stmt = select(QAQualityCheck).where(
            QAQualityCheck.qa_id == qa_id,
            QAQualityCheck.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        checks = list(result.scalars().all())

        total = len(checks)
        passed = sum(1 for c in checks if c.check_result)
        failed = total - passed
        blocking_failures = sum(1 for c in checks if not c.check_result and c.is_blocking)

        return {
            "qa_id": qa_id,
            "total_checks": total,
            "passed_checks": passed,
            "failed_checks": failed,
            "blocking_failures": blocking_failures,
            "overall_pass": blocking_failures == 0,
            "checks": checks,
        }

    # ========================================================================
    # 检查项实现
    # ========================================================================

    async def _check_source_support(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查1：答案是否由来源支持"""
        if not qa.sources:
            return False, 0.0, "未绑定任何来源文档或 Chunk"

        # 检查是否有来源包含引用文本
        has_quote = any(s.quote_text and len(s.quote_text) > 10 for s in qa.sources)
        if not has_quote:
            return False, 0.3, "来源绑定存在但缺少引用原文片段"

        return True, 1.0, "答案有明确的来源引用支持"

    async def _check_beyond_source(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查2：是否超出原文范围"""
        if not qa.sources:
            return True, 1.0, "无来源绑定，无法判断是否超出原文"

        # 简单检查：答案长度是否远超引用文本长度
        total_quote_len = sum(
            len(s.quote_text) for s in qa.sources if s.quote_text
        )
        answer_len = len(qa.answer)

        if total_quote_len > 0 and answer_len > total_quote_len * 3:
            return False, 0.4, f"答案长度({answer_len}字符)远超引用文本长度({total_quote_len}字符)，可能存在过度扩展"

        return True, 0.9, "答案长度与引用文本长度比例合理"

    async def _check_qa_match(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查3：问题和答案是否匹配"""
        question = qa.question.lower()
        answer = qa.answer.lower()

        # 检查答案是否包含问题中的关键词
        q_words = set(question.replace("?", "").replace("？", "").split())
        # 过滤常见停用词
        stop_words = {"是", "的", "了", "吗", "呢", "什么", "怎么", "如何", "为什么", "哪些", "哪个"}
        q_keywords = {w for w in q_words if w not in stop_words and len(w) > 1}

        if not q_keywords:
            return True, 0.8, "问题中无有效关键词，无法判断"

        matched = sum(1 for w in q_keywords if w in answer)
        ratio = matched / len(q_keywords)

        if ratio < 0.3:
            return False, ratio, f"答案中仅匹配到 {matched}/{len(q_keywords)} 个问题关键词"

        return True, ratio, f"答案匹配了 {matched}/{len(q_keywords)} 个问题关键词"

    async def _check_missing_conditions(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查4：是否缺少时间、地区、岗位等条件"""
        question = qa.question
        answer = qa.answer
        missing = []

        # 检查问题中是否包含时间相关词但答案中没有具体时间
        time_keywords = ["什么时候", "何时", "时间", "日期", "截止", "期限"]
        has_time_question = any(kw in question for kw in time_keywords)
        if has_time_question:
            time_patterns = [
                r"\d{4}年", r"\d{4}-\d{2}-\d{2}", r"每[年月周日]",
                r"每月", r"每年", r"季度", r"上半年", r"下半年",
            ]
            has_time_answer = any(re.search(p, answer) for p in time_patterns)
            if not has_time_answer:
                missing.append("时间/日期")

        # 检查地区相关
        location_keywords = ["哪里", "在哪", "地点", "地址", "地区", "哪个城市"]
        has_location_question = any(kw in question for kw in location_keywords)
        if has_location_question:
            # 简单检查答案中是否有地名相关词汇
            if "地点" not in answer.lower() and "地址" not in answer.lower():
                missing.append("地点/地址")

        if missing:
            return False, 0.5, f"缺少以下条件信息: {', '.join(missing)}"

        return True, 1.0, "答案包含了必要的条件信息"

    async def _check_duplicate_check(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查5：是否与已有问答重复"""
        # 查找与当前问答问题相似的已发布问答
        stmt = select(StandardQA).where(
            and_(
                StandardQA.id != qa.id,
                StandardQA.knowledge_base_id == qa.knowledge_base_id,
                StandardQA.deleted_at.is_(None),
                StandardQA.status.in_(["published", "pending_publish", "pending_review"]),
            )
        )
        result = await db.execute(stmt)
        existing_qas = list(result.scalars().all())

        for existing in existing_qas:
            similarity = self._text_similarity(qa.question, existing.question)
            if similarity > 0.85:
                return False, 1.0 - similarity, (
                    f"与已有问答 '{existing.id}' 高度相似（相似度: {similarity:.2%}），"
                    f"问题: '{existing.question[:50]}...'"
                )

        return True, 1.0, "未发现与已有问答重复"

    async def _check_sensitive_info(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查6：是否包含敏感信息"""
        combined_text = f"{qa.question} {qa.answer} {qa.short_answer or ''} {qa.detailed_answer or ''}"
        found_sensitive = []

        for pattern, label in SENSITIVE_PATTERNS:
            matches = re.findall(pattern, combined_text)
            if matches:
                found_sensitive.append(f"{label}(匹配到 {len(matches)} 处)")

        if found_sensitive:
            return False, 0.0, f"检测到敏感信息: {', '.join(found_sensitive)}"

        return True, 1.0, "未检测到敏感信息"

    async def _check_scope_expansion(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查7：是否扩大权限范围"""
        # 标准问答不得拥有比来源文档更大的访问范围
        if not qa.access_scope or not qa.sources:
            return True, 1.0, "无访问范围约束或无来源绑定"

        # 检查是否设置了过于宽泛的权限
        if qa.applicable_roles is None and qa.applicable_departments is None:
            return False, 0.3, "建议设置适用角色或适用部门，避免权限范围过大"

        # 检查 access_scope 是否包含通配符
        if qa.access_scope:
            for scope_key, scope_val in qa.access_scope.items():
                if isinstance(scope_val, list) and "*" in scope_val:
                    return False, 0.2, f"访问范围 '{scope_key}' 包含通配符，权限范围过大"

        return True, 0.9, "权限范围设置合理"

    async def _check_source_valid(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查8：来源文档是否有效"""
        if not qa.sources:
            return False, 0.0, "未绑定任何来源"

        # 检查是否有来源文档 ID
        for source in qa.sources:
            if not source.document_id:
                return False, 0.0, "来源绑定中缺少文档 ID"
            if not source.chunk_id:
                return False, 0.3, f"来源文档 {source.document_id} 缺少 Chunk 绑定"

        return True, 1.0, "所有来源绑定有效"

    async def _check_source_version_current(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查9：来源版本是否当前"""
        if not qa.sources:
            return True, 1.0, "无来源绑定"

        # 检查是否有版本号
        outdated = []
        for source in qa.sources:
            if source.document_version and source.document_version < 1:
                outdated.append(source.document_id)

        if outdated:
            return False, 0.5, f"以下来源文档版本可能已过时: {', '.join(outdated)}"

        return True, 0.9, "来源版本检查通过（需人工确认是否为最新版本）"

    async def _check_absolute_claims(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查10：是否使用绝对化但无依据的表述"""
        found_absolute = []

        for pattern in ABSOLUTE_PATTERNS:
            if re.search(pattern, qa.answer):
                found_absolute.append(pattern.replace("\\", ""))

        if found_absolute:
            return False, 0.4, (
                f"答案中包含绝对化表述: {', '.join(found_absolute[:5])}，"
                f"请确认是否有充分依据"
            )

        return True, 1.0, "未发现绝对化表述"

    async def _check_answer_completeness(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查11：答案完整性检查"""
        issues = []

        # 答案长度检查
        if len(qa.answer) < 20:
            issues.append("答案过短（少于20字符）")

        # 简短答案检查
        if not qa.short_answer:
            issues.append("缺少简短答案")

        # 详细答案检查
        if not qa.detailed_answer:
            issues.append("缺少详细答案")

        if issues:
            return False, 0.5, "; ".join(issues)

        return True, 1.0, "答案完整"

    async def _check_scope_reasonableness(
        self, db: AsyncSession, qa: StandardQA
    ) -> tuple[bool, float, str]:
        """检查12：适用范围合理性检查"""
        if not qa.effective_start and not qa.effective_end:
            return True, 1.0, "未设置生效时间范围"

        now = datetime.now(timezone.utc)

        # 检查生效时间是否已过
        if qa.effective_end and qa.effective_end < now:
            return False, 0.0, "生效结束时间已过，问答将不会生效"

        # 检查时间范围是否合理
        if qa.effective_start and qa.effective_end:
            if qa.effective_start >= qa.effective_end:
                return False, 0.0, "生效开始时间晚于或等于结束时间"

            # 检查时间范围是否过短（少于1天）
            delta = qa.effective_end - qa.effective_start
            if delta.days < 1:
                return False, 0.6, "生效时间范围过短（不足1天）"

        return True, 1.0, "生效时间范围合理"

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """计算文本相似度（基于词重叠的 Jaccard 相似度）"""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0


# 单例
qa_quality_check_service = QAQualityCheckService()