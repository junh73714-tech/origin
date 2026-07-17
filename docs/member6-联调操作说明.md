# 成员6 联调操作说明

本文档供成员6在 **PR 已提交** 后，向各相关成员说明「第二步：联调/签收」的具体操作。  
PR 地址：`http://192.168.51.25:3010/admin/origin/pulls/1`  
源分支：`feature/m6-hybrid-retrieval` → 目标分支：`develop`

---

## 一、第二步在做什么

| 阶段 | 内容 | 状态 |
|------|------|------|
| 第一步 | 推送功能分支、创建 PR | 已完成 |
| **第二步** | **各成员确认契约、评审、约联调** | **当前进行** |
| 第三步 | 本机/部署环境配置、迁移、冒烟测试 | 待定 |

第二步 **不要求各成员立刻改成员6代码**，主要是：

1. 确认接口、字段、行为是否与团队契约一致  
2. 明确 Mock/适配器何时可替换为正式实现  
3. 划分评审与联调责任，避免合并后无法对接  

---

## 二、成员1：公共变更评审

### 职责

成员6 对公共底座做了 **最小必要改动**，合并前需成员1确认不破坏冻结契约。

### 需要查看的文件

| 文件 | 说明 |
|------|------|
| `backend/app/models/base.py` | `BaseModel` 增加 `id` 主键 |
| `backend/app/api/auth.py` 等 | `*_router = router` 导出别名 |
| `backend/app/core/security.py` | `AccessContext` 扩展（scope_hash 等） |
| `backend/app/__init__.py` | 懒加载 app，便于单元测试 |
| `backend/alembic/versions/002_m6_retrieval_logs.py` | 新增 citations / query_logs / retrieval_logs |
| `backend/alembic/versions/001_initial.py` | 补 `import alembic.op as op` |
| `docs/api-contracts.md` | citations、cancel、debug 等增补（待签收） |

### 操作步骤

1. 打开 PR #1，切换到「文件变动」标签页。  
2. 重点审阅上表文件，对照 `docs/api-contracts.md`、`docs/data-model.md`、错误码与迁移规范。  
3. 在 PR 中发表评论：  
   - **通过**：说明公共部分可合并，或列出无阻塞小建议。  
   - **不通过**：逐条写明需修改项及原因。  
4. 在 Gitea 上标记评审状态（若团队启用 Review 功能）。

### 期望反馈给成员6

- 公共改动是否可合并  
- 契约文档增补是否可冻结  
- 迁移 002 的 upgrade/downgrade 是否需在 CI 中验证  

---

## 三、成员4：权限 PermissionService

### 职责

检索与问答必须在 **召回正文之前** 使用同一套权限规则。成员6 已实现 `permission_adapter` 适配层，需与成员4 正式 `PermissionService` 对齐。

### 成员6 当前适配的接口

```text
get_access_context()
build_retrieval_filters()
can_access_chunk()
can_access_standard_qa()
can_open_citation()
scope_hash（稳定权限摘要）
```

实现位置：`backend/app/retrieval/permission_adapter.py`

### 操作步骤

1. 阅读 PR 中 `permission_adapter.py` 与 `retrieval/types.py`（`RetrievalFilter`）。  
2. 对照成员4 正式实现，确认：  
   - 入参/出参字段是否与契约 JSON 一致  
   - 默认拒绝、显式拒绝优先、管理员不默认拥有全部文档阅读权  
   - `scope_hash` 计算规则是否一致（影响缓存隔离）  
3. 若正式服务已就绪：  
   - 提供 **类名、依赖注入方式、调用示例**  
   - 与成员6 约定替换 `DefaultPermissionAdapter` 的时间点  
4. 若尚未就绪：  
   - 确认适配器字段与 `docs` 契约一致  
   - 给出预计可用时间  

### 期望反馈给成员6

- 接口是否与 PR 中适配层一致  
- 正式服务何时可联调  
- 是否有字段/行为必须修改  

---

## 四、成员5：Embedding 与索引

### 职责

Keyword 检索依赖 OpenSearch，Vector 检索依赖 pgvector。查询向量 **必须** 使用成员5 唯一的 `EmbeddingProvider`，且 **模型与维度不得混用**。

### 成员6 当前状态

- Embedding：测试替身 `DeterministicEmbeddingProvider`（`backend/app/providers/embedding/provider.py`）  
- 索引：内存 Keyword/Vector 索引（`qa.py` 中演示接线；生产需替换）  

### 操作步骤

1. 确认并书面告知成员6：  
   - Embedding **模型名、版本、向量维度**（如 `text-embedding-3-small` / 1536）  
   - OpenSearch **索引名**、Chunk 字段是否与 `RetrievalHit` 一致  
   - pgvector **表结构**、向量列、与文档版本的关联方式  
2. 在测试环境准备：  
   - 至少 1 个知识库  
   - 若干 **已发布、当前版本** 的 Chunk 索引数据  
3. 索引写入完成后，通知成员6 将 API 层内存索引替换为真实客户端。  
4. 可选：与成员6 共同验证「无权限 Chunk 不进入召回」。

### 期望反馈给成员6

- 模型/维度/索引约定文档或配置项  
- 测试环境地址与可用时间  
- Chunk 元数据字段清单（含 status、is_current_version、confidentiality_level 等）  

---

## 五、成员7：标准问答匹配

### 职责

正式问答图 **优先** 调用标准问答匹配；仅当不可信命中时才走 RAG。成员6 **不得** 直接查询成员7 底层表或索引。

### 成员6 当前状态

- 适配器：`backend/app/rag/standard_qa_adapter.py`  
- 测试替身：`MockStandardQAMatcher`  

### 期望的 match 输出（契约参考）

```json
{
  "matched": true,
  "qa_id": "",
  "answer": "",
  "variants": [],
  "semantic_score": 0,
  "keyword_score": 0,
  "entity_consistency": 0,
  "scope_consistency": 0,
  "final_score": 0,
  "citations": [],
  "status": "",
  "reason": ""
}
```

可信命中需同时满足：已发布、权限一致、实体/范围一致、评分达标等（见成员6 任务书）。

### 操作步骤

1. 阅读 `standard_qa_adapter.py` 与 `graph.py` 中标准问答分支逻辑。  
2. 确认正式 `match_standard_qa(...)` 入参：  
   - 用户问题、关键词、实体、意图、`AccessContext`、知识库范围  
3. 提供测试环境调用方式（HTTP 或 Python 接口）。  
4. 与成员6 联调至少 3 类场景：  
   - 可信命中 → 直接返回标准答案  
   - 相似但实体不一致 → 转 RAG  
   - 未命中 → 走混合检索  

### 期望反馈给成员6

- 正式 match 接口定义与示例响应  
- 服务地址与联调时间  

---

## 六、成员2：用户端 SSE 与会话

### 职责

用户通过前端发起问答；成员6 提供 SSE 流式接口，成员2 按 **冻结契约** 消费事件。

### 相关接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/qa/chat` | 发送消息，SSE 流式返回 |
| POST | `/api/v1/qa/queries/{query_id}/cancel` | 取消进行中的查询 |
| GET | `/api/v1/qa/queries/{query_id}/stream` | 按 query_id 重放结果（重连扩展） |
| GET | `/api/v1/qa/conversations` | 会话列表 |
| GET | `/api/v1/qa/conversations/{id}` | 会话详情 |
| GET | `/api/v1/qa/citations/{citation_id}` | 引用详情（不含 MinIO 真实地址） |

### SSE 事件（契约最小集 + 扩展）

**必须处理（api-contracts）：**

- `event: message` — 增量/完成内容，完成时可带 `references`  
- `event: done` — 含 `conversation_id`、`message_id`；扩展含 `query_id`、完整 `answer`  

**扩展事件（可忽略未知事件）：**

- `message_start`、`answer_delta`、`citation`、`metadata`、`error`  

### 操作步骤

1. 使用有效 JWT 调用 `POST /api/v1/qa/chat`，`Content-Type: application/json`：  
   ```json
   { "conversation_id": null, "content": "测试问题" }
   ```  
2. 解析 SSE，以 **`done` 事件** 为最终完整结果依据。  
3. 从 `done` / `metadata` 读取 `query_id`，测试 `cancel` 与 `stream`（若前端需要重连）。  
4. 验证引用展示：仅使用 `citations` 中字段，不拼接内部存储路径。  
5. 发现问题在 PR 或群里反馈字段/事件名， **不要自行改后端路由**（由成员6/成员1 走 PR）。

### 期望反馈给成员6

- SSE 解析是否正常  
- 是否需要调整事件字段或路径（需走契约变更）  

---

## 七、成员3：管理后台与检索调试

### 职责

后台需展示检索全链路（改写、Keyword/Vector、RRF、证据、答案等）。成员6 提供 **受权限保护** 的调试接口。

### 接口

```text
POST /api/v1/qa/debug/query
```

**权限要求（满足其一）：**

- `system.configure`  
- `audit.read`  
- 或团队约定的后台调试权限  

**请求体示例：**

```json
{
  "content": "差旅报销需要什么材料",
  "knowledge_base_ids": ["kb_xxx"]
}
```

**响应要点：** 原始/改写问题、意图、关键词、各阶段 chunk_id 列表、证据分、答案、拒答原因、各阶段耗时、trace_id。  
**默认不返回** 无权限用户的完整敏感正文。

### 操作步骤

1. 使用具备调试权限的后台账号登录并携带 Bearer Token。  
2. 调用 `POST /api/v1/qa/debug/query`，检查返回字段是否满足后台页面展示需求。  
3. 使用 **无权限** 普通用户账号调用，确认返回 403。  
4. 在 PR 或需求单中反馈：还需哪些调试字段、是否与后台菜单权限码对齐。

### 期望反馈给成员6

- 调试 JSON 是否足够支撑后台 UI  
- 权限码是否与成员3 菜单配置一致  

---

## 八、成员6 自身在第二步的操作清单

| 序号 | 动作 | 说明 |
|------|------|------|
| 1 | 将本文档或 PR 链接发至各成员 | 可按成员分段转发 |
| 2 | 记录签收表 | 谁已回复、谁阻塞、预计时间 |
| 3 | **不要自行合并 PR** | 等成员1 及必要评审完成 |
| 4 | 收到正式接口后 | 在 `feature/m6-hybrid-retrieval` 上替换 Mock，push 更新同一 PR |
| 5 | 联调问题 | 在 PR 评论中 @ 对应成员，避免私改他人模块 |

### 签收记录表（成员6 自用）

| 成员 | 事项 | 已通知 | 已回复 | 联调时间 | 备注 |
|------|------|--------|--------|----------|------|
| 成员1 | 公共变更评审 | ☐ | ☐ | | |
| 成员4 | PermissionService | ☐ | ☐ | | |
| 成员5 | Embedding/索引 | ☐ | ☐ | | |
| 成员7 | 标准问答 match | ☐ | ☐ | | |
| 成员2 | SSE/会话 | ☐ | ☐ | | |
| 成员3 | debug 接口 | ☐ | ☐ | | |

---

## 九、已知 Mock / 阻塞项（供各成员知悉）

以下项 **不阻塞 PR 评审**，但 **阻塞生产验收**，需对应成员就绪后替换：

| 项 | 当前实现 | 依赖 |
|----|----------|------|
| LLM | MockLLMProvider | 团队选定真实 LLM |
| Reranker | MockRerankerProvider | 团队选定真实 Reranker |
| Embedding | 确定性测试替身 | 成员5 正式 Provider |
| 权限 | DefaultPermissionAdapter | 成员4 正式 PermissionService |
| 标准问答 | MockStandardQAMatcher | 成员7 正式 match 服务 |
| 会话持久化 | 进程内存储（结构对齐 DB 表） | 联调通过后可选接 SQLAlchemy |
| 检索索引 | 空内存索引 | 成员5 OpenSearch/pgvector 数据 |

---

## 十、测试命令（供评审人本地验证成员6 定向测试）

```bash
cd backend
python -m pytest tests/retrieval tests/rag tests/conversation -v
```

当前预期：**27 passed**（以 PR 最新提交为准）。

---

## 十一、联系方式与文档索引

| 文档 | 路径 |
|------|------|
| PR 正文模板 | `docs/member6-pr-body.md` |
| 模块说明 | `docs/member6-module.md` |
| API 契约 | `docs/api-contracts.md` |
| 成员6 检索 README | `backend/app/retrieval/README.md` |
| 成员6 RAG README | `backend/app/rag/README.md` |

---

**文档版本：** 与 PR #1（含提交 `ee575dc` 及之后更新）对应  
**维护：** 成员6；公共契约变更需成员1 评审后更新本文档
