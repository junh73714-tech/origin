# 成员5 跨模块接口契约

> 本文档是成员5与上下游模块的接口约定。
> 成员5保证按此契约提供能力，调用方按此契约消费。
> 接口变更必须通过 PR 评审并同步更新本文档。

---

## 1. 我依赖谁（上游契约）

### 1.1 成员4：权限服务

| 接口 | 说明 |
|------|------|
| `PermissionService.get_access_context(tenant_id, user_id, resource_type, resource_id)` | 获取用户访问上下文 |
| `PermissionService.check_permission(tenant_id, user_id, action, resource_type, resource_id)` | 检查操作权限 |

**AccessContext 结构（待成员4冻结）**：

```json
{
    "tenant_id": "string",
    "user_id": "string",
    "role_ids": ["string"],
    "department_ids": ["string"],
    "group_ids": ["string"],
    "knowledge_base_ids": ["string"],
    "max_confidentiality_level": 0,
    "deny_document_ids": ["string"],
    "temporary_grants": [],
    "scope_hash": "string"
}
```

**我的责任**：文档权限继承知识库权限，Chunk 权限继承文档权限，将 `AccessContext` 快照和 `scope_hash` 写入 `permission_metadata` 字段。

### 1.2 成员1：公共基础设施

| 接口 | 说明 |
|------|------|
| 统一响应格式 | `{success, data, message, request_id}` / `{success, error, request_id}` |
| 统一错误码 | `app.core.exceptions` 中定义的异常体系 |
| 分页格式 | `page` + `page_size`（offset + limit） |
| 时间格式 | ISO 8601 |
| 日志规范 | 结构化 JSON，含 `request_id` 和 `trace_id` |
| 数据库会话 | `AsyncSession` 通过 `get_db()` 依赖注入 |

---

## 2. 谁依赖我（下游契约）

### 2.1 提供给成员6：检索与问答

| 接口 | 说明 | 状态 |
|------|------|------|
| `EmbeddingProvider.get_model_info()` | 获取当前模型名称、维度、版本号 | 已实现 |
| `EmbeddingProvider.embed_query(text)` | 生成查询向量 | 已实现 |
| `IndexingService.get_index_status(document_version_id)` | 查询双索引状态 | 待封装 |
| Chunk 索引结构 | OpenSearch 中的文档字段定义 | 见下文 |
| Chunk 向量结构 | pgvector 中的向量存储结构 | 见下文 |

**OpenSearch 索引文档结构**：

```json
{
    "chunk_id": "string",
    "document_id": "string",
    "document_version_id": "string",
    "knowledge_base_id": "string",
    "tenant_id": "string",
    "chunk_no": 0,
    "title_path": "第一章 > 第一节 > 概述",
    "clean_text": "text for BM25 search",
    "page_start": 1,
    "page_end": 2,
    "token_count": 150,
    "status": "active",
    "permission_metadata": {"scope_hash": "abc", "allow_roles": ["reader"]},
    "created_at": "2026-01-01T00:00:00Z"
}
```

**成员6读取规则**：

- 只从 OpenSearch 和 pgvector 读取索引数据（只读）
- 不得直接写入 OpenSearch 或 pgvector
- 查询向量必须通过 `EmbeddingProvider.embed_query()` 生成
- 检索时必须应用 `permission_metadata` 中的权限过滤条件
- 只检索 `status == "published"` 且 `is_current_version == true` 的文档的 Chunk

### 2.2 提供给成员7：标准问答与评估

| 接口 | 说明 | 状态 |
|------|------|------|
| Outbox 事件：`document.version.published` | 新版本发布，标记相关问答待复核 | 已实现 |
| Outbox 事件：`document.offlined` | 文档下线，相关问答立即失效 | 已实现 |
| Outbox 事件：`document.permission.changed` | 权限变更，相关问答权限重检 | 预留 |
| Outbox 事件：`document.index.completed` | 索引完成通知 | 已实现 |
| `DocumentVersionService.get_current_version(document_id)` | 获取当前生效版本信息 | 待封装 |

### 2.3 提供给成员3：管理后台数据

成员3通过以下 API 端点获取所有管理后台所需的文档和知识库数据：

| 端点 | 用途 |
|------|------|
| GET /knowledge-bases | 知识库列表页面 |
| GET /knowledge-bases/{id} | 知识库详情 |
| GET /knowledge-bases/{id}/stats | 工作台统计卡片 |
| GET /documents | 文档列表页面 |
| GET /documents/{id} | 文档详情（含处理进度、失败原因） |
| GET /documents/{id}/versions | 版本列表页面 |
| GET /document-chunks | Chunk 查看页面 |
| GET /index-tasks | 索引任务列表页面 |
| POST /index-tasks/{id}/retry | 重试按钮 |

---

## 3. 我发送的 Outbox 事件（全量契约）

所有事件与数据库状态变更在同一事务中写入 `outbox_events` 表。消费者必须幂等处理。

| 事件类型 | aggregate_type | 触发时机 | Payload | 消费者 |
|----------|---------------|----------|---------|--------|
| `document.version.created` | document | 新版本创建 | `{document_id, old_version_id, new_version_id, old_version, new_version, diff}` | 成员1 |
| `document.version.published` | document | 版本发布成功 | `{document_id, version_id, version, knowledge_base_id, published_at}` | 成员6, 成员7 |
| `document.paused` | document | 文档暂停 | `{document_id, version_id, knowledge_base_id}` | 成员6 |
| `document.offlined` | document | 文档下线 | `{document_id, version_id, knowledge_base_id}` | 成员6, 成员7 |
| `document.permission.changed` | document | 权限变更 | `{document_id, knowledge_base_id, changes}` | 成员6, 成员7 |
| `document.index.completed` | document | 索引完成 | `{document_id, document_version_id, chunk_count, indexed_count, knowledge_base_id}` | 成员6, 成员1 |

---

## 4. 成员6/7 对我的约束（必须遵守）

- 文档状态为 `published` 且 `is_current_version == true` 且未过期且权限有效时，才能被成员6检索
- 文档下线后（`offline`），应立即从正式召回范围排除
- 新版本未发布前，旧版本必须保持可用（`is_current_version == true`）
- 成员6只能通过 `EmbeddingProvider` 获取查询向量，不得创建第二套 Embedding 配置
- 成员7只能消费 Outbox 事件，不得绕过事件直接轮询数据库状态
- OCR 不可用时必须明确标记为 `degraded`，不得伪造 OCR 结果

---

## 5. 未冻结项（待联调确认）

| 项目 | 责任人 | 状态 |
|------|--------|------|
| `AccessContext` 完整字段结构 | 成员4 | 待冻结 |
| `PermissionService` 接口签名 | 成员4 | 待冻结 |
| OpenSearch 索引 mapping 最终方案 | 成员5+6 | 待联调 |
| pgvector `chunk_vectors` 表结构 | 成员5+6 | 待联调 |
| 文件大小上限最终值 | 团队 | 当前默认100MB |
| Chunk token 上限/重叠窗口 最终值 | 成员5+6 | 当前默认500/50 |

---

## 6. 变更记录

| 日期 | 变更内容 | 作者 |
|------|----------|------|
| 2026-07-16 | 初始版本，覆盖 M1-M4 全部接口 | 成员5 |
