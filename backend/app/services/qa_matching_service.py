"""
标准问答匹配服务（成员7）
提供标准问答匹配能力，供成员6的正式问答链路调用
复用成员5提供的 EmbeddingProvider 进行语义匹配
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.qa import QAStatus, QuestionVariant, StandardQA

logger = get_logger(__name__)


class QAMatchingService:
    """标准问答匹配服务"""

    # 综合评分权重
    SEMANTIC_WEIGHT = 0.40
    KEYWORD_WEIGHT = 0.25
    ENTITY_WEIGHT = 0.20
    SCOPE_WEIGHT = 0.15

    # 默认阈值
    DEFAULT_THRESHOLD = 0.70

    def __init__(self, embedding_provider=None):
        """
        初始化匹配服务
        embedding_provider: 成员5提供的 EmbeddingProvider 实例，用于语义匹配
        """
        self._embedding_provider = embedding_provider

    def set_embedding_provider(self, provider) -> None:
        """设置 Embedding Provider（由成员5提供）"""
        self._embedding_provider = provider

    async def match(
        self,
        db: AsyncSession,
        query: str,
        keywords: list[str] | None = None,
        entities: list[str] | None = None,
        intent: str = "",
        access_context: dict | None = None,
        knowledge_base_ids: list[str] | None = None,
        top_k: int = 5,
        threshold: float = 0.70,
        trusted_threshold: float = 0.85,
    ) -> dict[str, Any]:
        """
        执行标准问答匹配

        匹配条件（全部满足才可命中）：
        1. 已审核、已发布、未过期
        2. 来源文档有效
        3. 权限一致
        4. 角色和部门适用
        5. 核心实体一致
        6. 综合评分达到阈值
        """
        keywords = keywords or []
        entities = entities or []
        access_context = access_context or {}
        knowledge_base_ids = knowledge_base_ids or []

        start_time = datetime.now(timezone.utc)

        # 1. 获取候选标准问答（已发布、未过期、权限匹配）
        candidates = await self._get_candidates(
            db, access_context, knowledge_base_ids
        )

        if not candidates:
            return {
                "matched": False,
                "results": [],
                "query": query,
                "processing_time_ms": 0.0,
            }

        # 2. 对每个候选进行多维度评分
        results = []
        for qa in candidates:
            scores = await self._score_candidate(
                qa, query, keywords, entities, intent, access_context
            )

            final_score = self._compute_final_score(scores)
            if final_score >= threshold:
                # 计算 trusted 标志
                trusted = (
                    qa.status == QAStatus.PUBLISHED
                    and final_score >= trusted_threshold
                    and scores.get("entity_consistency", 0.0) >= 1.0
                    and scores.get("scope_consistency", 0.0) >= 1.0
                )

                # 获取来源文档ID列表和知识库ID
                source_document_ids = list({source.document_id for source in (qa.sources or [])})
                knowledge_base_id = qa.knowledge_base_id

                results.append({
                    "matched": True,
                    "trusted": trusted,
                    "qa_id": qa.id,
                    "question": qa.question,
                    "answer": qa.answer,
                    "short_answer": qa.short_answer,
                    "detailed_answer": qa.detailed_answer,
                    "variants": self._get_active_variant_texts(qa),
                    "semantic_score": scores.get("semantic_score", 0.0),
                    "keyword_score": scores.get("keyword_score", 0.0),
                    "entity_consistency": scores.get("entity_consistency", 0.0),
                    "scope_consistency": scores.get("scope_consistency", 0.0),
                    "final_score": round(final_score, 4),
                    "citations": self._build_citations(qa),
                    "source_document_ids": source_document_ids,
                    "knowledge_base_id": knowledge_base_id,
                    "status": qa.status,
                    "reason": "匹配成功",
                })

        # 3. 按综合评分排序，取 top_k
        results.sort(key=lambda x: x["final_score"], reverse=True)
        results = results[:top_k]

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        # 4. 更新命中计数
        if results and results[0]["matched"]:
            await self._increment_use_count(db, results[0]["qa_id"])

        return {
            "matched": len(results) > 0,
            "results": results,
            "query": query,
            "processing_time_ms": round(elapsed, 2),
        }

    async def _get_candidates(
        self,
        db: AsyncSession,
        access_context: dict,
        knowledge_base_ids: list[str],
    ) -> list[StandardQA]:
        """获取候选标准问答列表"""
        now = datetime.now(timezone.utc)

        conditions = [
            StandardQA.status == QAStatus.PUBLISHED,
            StandardQA.deleted_at.is_(None),
            # 未过期
            or_(
                StandardQA.effective_end.is_(None),
                StandardQA.effective_end > now,
            ),
            # 已生效
            or_(
                StandardQA.effective_start.is_(None),
                StandardQA.effective_start <= now,
            ),
        ]

        # 知识库过滤
        if knowledge_base_ids:
            conditions.append(StandardQA.knowledge_base_id.in_(knowledge_base_ids))

        # 权限过滤：过滤适用角色和部门
        user_roles = access_context.get("roles", [])
        user_departments = access_context.get("departments", [])
        user_tenant = access_context.get("tenant_id", "")

        if user_tenant:
            conditions.append(StandardQA.tenant_id == user_tenant)

        stmt = (
            select(StandardQA)
            .where(and_(*conditions))
            .order_by(StandardQA.priority.desc(), StandardQA.use_count.desc())
            .limit(200)  # 限制候选数量，避免全表扫描
        )
        result = await db.execute(stmt)
        all_candidates = list(result.scalars().all())

        # 权限过滤：在应用层过滤（因为 JSONB 字段无法高效索引）
        filtered = []
        for qa in all_candidates:
            if self._check_access_scope(qa, user_roles, user_departments):
                filtered.append(qa)

        return filtered

    def _check_access_scope(
        self,
        qa: StandardQA,
        user_roles: list[str],
        user_departments: list[str],
    ) -> bool:
        """检查访问范围是否匹配"""
        # 如果问答没有设置适用角色和部门，默认允许所有
        if not qa.applicable_roles and not qa.applicable_departments:
            return True

        # 角色匹配
        if qa.applicable_roles:
            role_match = any(r in qa.applicable_roles for r in user_roles)
            if not role_match:
                return False

        # 部门匹配
        if qa.applicable_departments:
            dept_match = any(d in qa.applicable_departments for d in user_departments)
            if not dept_match:
                return False

        return True

    async def _score_candidate(
        self,
        qa: StandardQA,
        query: str,
        keywords: list[str],
        entities: list[str],
        intent: str,
        access_context: dict,
    ) -> dict[str, float]:
        """对候选问答进行多维度评分"""
        scores: dict[str, float] = {}

        # 语义相似度评分（通过 EmbeddingProvider）
        scores["semantic_score"] = await self._compute_semantic_score(qa, query)

        # 关键词匹配评分
        scores["keyword_score"] = self._compute_keyword_score(qa, keywords)

        # 实体一致性评分
        scores["entity_consistency"] = self._compute_entity_consistency(qa, entities)

        # 适用范围一致性评分
        scores["scope_consistency"] = self._compute_scope_consistency(qa, access_context)

        return scores

    async def _compute_semantic_score(
        self,
        qa: StandardQA,
        query: str,
    ) -> float:
        """计算语义相似度评分"""
        if self._embedding_provider is None:
            # 无 EmbeddingProvider 时使用简单的文本重叠度
            return self._fallback_text_similarity(qa.question, query)

        try:
            # 使用成员5的 EmbeddingProvider 进行语义匹配
            # 同时匹配标准问题和所有活跃变体
            texts_to_compare = [qa.question]
            for variant in qa.variants:
                if variant.is_active:
                    texts_to_compare.append(variant.variant_text)

            query_embedding = await self._embedding_provider.embed_query(query)
            max_similarity = 0.0

            for text in texts_to_compare:
                text_embedding = await self._embedding_provider.embed_query(text)
                similarity = self._cosine_similarity(query_embedding, text_embedding)
                max_similarity = max(max_similarity, similarity)

            return max_similarity
        except Exception as e:
            logger.warning("semantic_score_failed", error=str(e), qa_id=qa.id)
            return self._fallback_text_similarity(qa.question, query)

    def _fallback_text_similarity(self, text1: str, text2: str) -> float:
        """降级文本相似度计算（基于词重叠）"""
        if not text1 or not text2:
            return 0.0
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        return len(intersection) / max(len(words1), len(words2))

    def _compute_keyword_score(
        self,
        qa: StandardQA,
        keywords: list[str],
    ) -> float:
        """计算关键词匹配评分"""
        if not keywords:
            return 0.5  # 无关键词输入时给中等分

        qa_keywords = qa.keywords or []
        if not qa_keywords:
            return 0.3

        matched = 0
        for kw in keywords:
            kw_lower = kw.lower()
            for qa_kw in qa_keywords:
                if isinstance(qa_kw, str) and kw_lower in qa_kw.lower():
                    matched += 1
                    break

        return matched / len(keywords) if keywords else 0.0

    def _compute_entity_consistency(
        self,
        qa: StandardQA,
        entities: list[str],
    ) -> float:
        """计算核心实体一致性评分"""
        if not entities:
            return 0.5  # 无实体输入时给中等分

        qa_entities = qa.core_entities or []
        if not qa_entities:
            return 0.3

        matched = 0
        for entity in entities:
            entity_lower = entity.lower()
            for qa_entity in qa_entities:
                if isinstance(qa_entity, str) and entity_lower in qa_entity.lower():
                    matched += 1
                    break

        return matched / len(entities) if entities else 0.0

    def _compute_scope_consistency(
        self,
        qa: StandardQA,
        access_context: dict,
    ) -> float:
        """计算适用范围一致性评分"""
        user_roles = access_context.get("roles", [])
        user_departments = access_context.get("departments", [])

        if not qa.applicable_roles and not qa.applicable_departments:
            return 1.0  # 无限制，完美匹配

        score = 1.0

        # 角色匹配度
        if qa.applicable_roles:
            if not user_roles:
                score *= 0.3
            else:
                matched = sum(1 for r in user_roles if r in qa.applicable_roles)
                score *= matched / len(qa.applicable_roles) if qa.applicable_roles else 0.5

        # 部门匹配度
        if qa.applicable_departments:
            if not user_departments:
                score *= 0.3
            else:
                matched = sum(1 for d in user_departments if d in qa.applicable_departments)
                score *= matched / len(qa.applicable_departments) if qa.applicable_departments else 0.5

        return score

    def _compute_final_score(self, scores: dict[str, float]) -> float:
        """计算综合评分"""
        return (
            scores.get("semantic_score", 0.0) * self.SEMANTIC_WEIGHT
            + scores.get("keyword_score", 0.0) * self.KEYWORD_WEIGHT
            + scores.get("entity_consistency", 0.0) * self.ENTITY_WEIGHT
            + scores.get("scope_consistency", 0.0) * self.SCOPE_WEIGHT
        )

    def _get_active_variant_texts(self, qa: StandardQA) -> list[str]:
        """获取活跃的问题变体文本"""
        if not qa.variants:
            return []
        return [v.variant_text for v in qa.variants if v.is_active]

    def _build_citations(self, qa: StandardQA) -> list[dict]:
        """构建引用来源列表"""
        citations = []
        for source in (qa.sources or []):
            citations.append({
                "document_id": source.document_id,
                "document_version": source.document_version,  # 整数版本号
                "document_version_id": f"doc_{source.document_id}_v{source.document_version}",  # 占位符，需与成员5对齐
                "chunk_id": source.chunk_id,
                "knowledge_base_id": source.knowledge_base_id,
                "is_primary": source.is_primary,
                "relevance_score": source.relevance_score,
                "quote_text": source.quote_text,
            })
        return citations

    async def _increment_use_count(self, db: AsyncSession, qa_id: str) -> None:
        """增加问答命中计数"""
        from sqlalchemy import update

        await db.execute(
            update(StandardQA)
            .where(StandardQA.id == qa_id)
            .values(use_count=StandardQA.use_count + 1)
        )

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)


# 单例
qa_matching_service = QAMatchingService()