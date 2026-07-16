# 成员6 混合检索模块

## 职责

- Keyword Retrieval（OpenSearch BM25，权限过滤在召回前）
- Vector Retrieval（pgvector + 成员5 EmbeddingProvider 适配）
- 去重与 Reciprocal Rank Fusion
- 检索调试摘要

## 关键类型

- `RetrievalFilter`：与 AccessContext / 成员4 对齐的统一过滤语义（含 `user_id`）
- `TemporaryGrantRef`：临时授权对象，对齐成员4 `TemporaryGrantInfo`；过滤时用属性 `temporary_grant_document_ids` 提取文档 ID
- `RetrievalHit`：双路统一候选结构

## 权限

通过 `permission_adapter.DefaultPermissionAdapter` 适配成员4接口：

- `build_retrieval_filters`
- `can_access_chunk`
- `can_access_standard_qa`
- `can_open_citation`

规则：默认拒绝、显式拒绝优先、系统管理员不默认拥有全部业务文档阅读权。

## 测试

```bash
cd backend
pytest tests/retrieval -v
```
