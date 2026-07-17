# 成员5 联调操作说明

本文档供成员5在 **PR 已提交** 后，向各相关成员说明「第二步：联调/签收」的具体操作。
PR 地址：`http://192.168.51.25:3010/admin/origin/pulls/9`
源分支：`feature/m5-document-pipeline` -> 目标分支：`develop`

---

## 一、第二步在做什么

| 阶段 | 内容 | 状态 |
|------|------|------|
| 第一步 | 推送功能分支、创建 PR #8 | 已完成 |
| **第二步** | **各成员确认契约、评审、约联调** | **当前进行** |
| 第三步 | Docker 环境部署、迁移执行、集成测试 | 待定 |

第二步 **不要求各成员立刻改成员5代码**，主要是：

1. 确认接口、字段、数据结构是否与团队契约一致
2. 明确 Mock/占位何时可替换为正式实现
3. 划分评审与联调责任，避免合并后无法对接

---

## 二、成员1：公共变更评审

### 职责

成员5 对公共底座做了 **最小必要改动**，合并前需成员1确认不破坏冻结契约。

### 需要查看的文件

| 文件 | 说明 |
|------|------|
| `backend/app/core/config.py` | 嵌套 Settings 补 Pydantic v2 类型注解 |
| `backend/app/main.py` | 修正 settings 引用 + 路由别名 + 注册 index-tasks/document-chunks 路由 |
| `backend/app/models/base.py` | BaseModel 增加 id 主键 + UUID 生成 |
| `backend/app/models/auth.py` | mapped_column 改为 Column（Table 兼容） |
| `backend/app/models/qa.py` | metadata 字段改名（SQLAlchemy 保留字冲突） |
| `backend/app/__init__.py` | 懒加载 app，避免循环导入 |
| `backend/alembic/versions/002_member5_models.py` | 4新表 + 21新字段 + chunk_vectors |
| `.gitignore` | 新增 reports/ 排除项 |

### 操作步骤

1. 打开 PR #8，切换到「文件变动」标签页。
2. 重点审阅上表文件，对照 `docs/api-contracts.md`、错误码与迁移规范。
3. 在 PR 中发表评论：
   - **通过**：说明公共部分可合并，或列出无阻塞小建议。
   - **不通过**：逐条写明需修改项及原因。
4. 在 Gitea 上标记评审状态。

### 期望反馈给成员5

- 公共改动是否可合并
- 迁移 002 的 upgrade/downgrade 是否需在 CI 中验证
- 路由注册方式是否与规范一致

---

## 三、成员4：权限 PermissionService

### 职责

文档权限继承知识库权限，Chunk 权限继承文档权限。成员5 已预留完整的权限元数据字段，需与成员4 正式 `PermissionService` 对齐。

### 成员5 当前状态

- 权限模型：`KnowledgeBasePermission`、`DocumentPermission`（`models/document.py`）
- Chunk 权限：`permission_metadata` 字段（JSON，存储 AccessContext 快照 + scope_hash）
- 权限校验：当前使用 `user_id="system"` 占位，待对接正式服务

### 成员5 需要成员4 提供

```text
PermissionService.get_access_context(tenant_id, user_id, resource_type, resource_id)
  -> AccessContext（含 scope_hash）

PermissionService.check_permission(tenant_id, user_id, action, resource_type, resource_id)
  -> bool
```

### 操作步骤

1. 阅读 PR #8 中 `models/document.py` 的 `KnowledgeBasePermission`、`DocumentPermission`、`DocumentChunk.permission_metadata`。
2. 对照成员4 正式实现，确认：
   - 权限模型字段是否与权限规则匹配
   - `permission_metadata` 中的 `scope_hash` 计算规则是否一致
   - 文档->Chunk 权限继承链路是否正确
3. 若正式服务已就绪：
   - 提供类名、依赖注入方式、调用示例
   - 与成员5 约定替换占位 `user_id="system"` 的时间点
4. 若尚未就绪：
   - 确认模型字段与契约一致
   - 给出预计可用时间

### 期望反馈给成员5

- 权限模型字段是否需要调整
- 正式 PermissionService 何时可联调
- `scope_hash` 计算规则

---

## 四、成员6：检索与问答（成员5 需要告知的内容）

### 成员5 已提供给成员6

| 提供项 | 详情 | 位置 |
|--------|------|------|
| EmbeddingProvider | `embed_query(text)` 生成查询向量；`get_model_info()` 返回模型名/维度/版本 | `providers/embedding.py` |
| 模型信息 | text-embedding-3-small / 1536维 / model_version(MD5) | `EmbeddingProvider.get_model_info()` |
| OpenSearch 索引 | 索引名 `rag_chunks`，文档结构含 chunk_id/title_path/clean_text/page/status/permission_metadata 等 | `services/indexing.py` + `docs/member5-contracts.md` |
| pgvector 表 | 表名 `chunk_vectors`，向量列 `embedding`(JSON数组)，dimension=1536，关联 document_version_id | 迁移 002 + `services/indexing.py` |
| 权限过滤 | 每个 Chunk 带 `permission_metadata`（含 scope_hash），检索时按此过滤 | `models/document.py` DocumentChunk |
| 文档状态 | 只有 published + is_current_version=true + 未过期 + 权限有效的文档可被检索 | `services/orchestrator.py` |

### 成员6 需要配合的事项

1. 查询向量必须通过 `EmbeddingProvider.embed_query()` 生成，不创建第二套 Embedding 配置
2. 检索时必须应用 `permission_metadata` 中的权限过滤条件
3. OpenSearch 和 pgvector 均只读，不写入
4. 收到 `document.offlined` Outbox 事件后立即停止检索该文档

---

## 五、成员7：标准问答与版本联动

### 职责

文档更新和下线需触发标准问答的待复核和失效操作。

### 成员5 发出的 Outbox 事件

| 事件类型 | 触发时机 | 成员7 应处理 |
|----------|----------|-------------|
| `document.version.published` | 新版本发布成功 | 找到受影响问答，标记待复核 |
| `document.offlined` | 文档下线 | 相关问答立即失效 |
| `document.permission.changed` | 权限变更 | 重检相关问答权限 |
| `document.index.completed` | 索引写入完成 | 确认文档可进入发布流程 |

### 事件格式

```json
{
  "event_type": "document.version.published",
  "aggregate_type": "document",
  "aggregate_id": "doc-001",
  "payload": {
    "document_id": "doc-001",
    "version_id": "ver-002",
    "version": 2,
    "knowledge_base_id": "kb-001",
    "published_at": "2026-07-16T00:00:00Z"
  }
}
```

完整事件格式见 `docs/member5-contracts.md` 第3节。

### 操作步骤

1. 阅读 `docs/member5-contracts.md` 第3节全部6种事件格式。
2. 确认消费侧对每种事件的处理逻辑：
   - 已发布的标准问答 -> 来源文档更新 -> 标记待复核
   - 已发布的标准问答 -> 来源文档下线 -> 问答失效
3. 与成员5 联调：触发一个文档发布，验证 Outbox 事件是否正确发出。
4. 确认事件处理幂等（重复事件不重复下线问答）。

### 期望反馈给成员5

- 事件格式是否需要调整
- 消费侧何时可联调
- 是否有需要新增的事件类型

---

## 六、成员3：后台管理页面

### 职责

管理后台需要展示知识库、文档、Chunk、索引任务的完整数据。

### 成员5 提供的后台接口

| 端点 | 用途 | 后台页面 |
|------|------|----------|
| GET /api/v1/knowledge-bases | 知识库列表（分页+搜索+状态筛选） | 知识库管理 |
| GET /api/v1/knowledge-bases/{id} | 知识库详情 | 知识库编辑 |
| GET /api/v1/knowledge-bases/{id}/stats | 文档/Chunk/索引统计 | 工作台 |
| GET /api/v1/documents | 文档列表（分页+状态+类型筛选） | 文档管理 |
| GET /api/v1/documents/{id} | 文档详情（含处理进度+失败原因） | 文档详情 |
| GET /api/v1/documents/{id}/versions | 版本列表 | 版本管理 |
| GET /api/v1/document-chunks | Chunk列表（分页+搜索） | Chunk查看 |
| GET /api/v1/document-chunks/{id} | Chunk详情（含原始文本） | Chunk详情 |
| GET /api/v1/index-tasks | 索引任务列表（分页+状态筛选） | 任务监控 |
| POST /api/v1/index-tasks/{id}/retry | 重试失败任务 | 任务操作 |

### 操作步骤

1. 确认后台页面需要的字段是否在接口响应中。
2. 长任务（文档处理、索引写入）需展示进度和失败原因，对应字段：
   - `Document.status` + `processing_error`
   - `IndexTask.progress` + `error_message`
3. 发布、下线等操作前展示影响说明（是否影响检索、是否触发问答复核）。
4. 发现问题在 PR 或群里反馈，**不要自行改后端路由**。

### 期望反馈给成员5

- 接口响应字段是否满足后台页面需求
- 是否需要增加筛选条件或字段

---

## 七、成员5 自身在第二步的操作清单

| 序号 | 动作 | 说明 |
|------|------|------|
| 1 | 将本文档或 PR 链接发至各成员 | 可按成员分段转发 |
| 2 | 记录签收表 | 谁已回复、谁阻塞、预计时间 |
| 3 | **不要自行合并 PR** | 等成员1 及必要评审完成 |
| 4 | 收到成员4 正式接口后 | 替换 `user_id="system"` 占位，push 更新同一 PR |
| 5 | 收到成员6 确认后 | 确认 Embedding 和索引字段对接无误 |
| 6 | 联调问题 | 在 PR 评论中 @ 对应成员，避免私改他人模块 |

### 签收记录表（成员5 自用）

| 成员 | 事项 | 已通知 | 已回复 | 联调时间 | 备注 |
|------|------|--------|--------|----------|------|
| 成员1 | 公共变更评审 | ☐ | ☐ | | |
| 成员4 | PermissionService | ☐ | ☐ | | |
| 成员6 | Embedding/索引契约 | ☐ | ☐ | | |
| 成员7 | Outbox 事件 | ☐ | ☐ | | |
| 成员3 | 后台接口 | ☐ | ☐ | | |

---

## 八、已知 Mock / 阻塞项（供各成员知悉）

以下项 **不阻塞 PR 评审**，但 **阻塞生产验收**，需对应成员就绪后替换：

| 项 | 当前实现 | 依赖 |
|----|----------|------|
| 权限 | `user_id="system"` 占位 | 成员4 正式 PermissionService |
| Embedding | 真实 OpenAI API 调用（Mock 测试时使用 mock） | 团队确认 Embedding 服务 |
| OCR | OCRProvider.process_image 占位返回空 | 团队选定 OCR 服务 |
| MinIO | 真实 MinIO 客户端（单元测试 Mock） | Docker 环境部署 |
| OpenSearch | 真实客户端（单元测试 Mock） | Docker 环境部署 |
| pgvector | 原始 SQL 写入（单元测试 Mock） | Docker 环境部署 |
| Celery | 真实 Worker（单元测试直接 await） | Docker 环境部署 |

---

## 九、测试命令（供评审人本地验证成员5 定向测试）

```bash
cd backend
python -m pytest tests/unit/ -k "not test_config and not test_access_context_super_admin" -v
```

当前预期：**284 passed**（以 PR 最新提交为准）。

---

## 十、文档索引

| 文档 | 路径 |
|------|------|
| PR #8 | `http://192.168.51.25:3010/admin/origin/pulls/9` |
| 架构图与流程图 | `docs/member5-architecture.md` |
| 跨模块接口契约 | `docs/member5-contracts.md` |
| 交付清单与验收 | `docs/member5-checklist.md` |
| CLAUDE.md | 项目根目录 `CLAUDE.md` |

---

**文档版本：** 与 PR #8 对应
**维护：** 成员5；公共契约变更需成员1 评审后更新本文档
