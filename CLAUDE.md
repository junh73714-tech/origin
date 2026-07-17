# CLAUDE.md -- 成员5：知识库、文档处理、版本与索引写入

> 本文件是 Claude Code 辅助成员5开发时的行为准则，所有代码生成、测试、提交必须遵守。

---

## 1. 角色定位

我是**成员5**，负责知识从上传到正式可检索的完整生命周期：

- 知识库 CRUD 与状态管理
- 文档上传、存储（MinIO）、解析、清洗
- 文档切分（Chunk）与版本管理
- Embedding 生成与向量写入（pgvector）
- 关键词索引写入（OpenSearch BM25）
- 索引任务调度与一致性保障
- OCR Provider 实现
- EmbeddingProvider 共享实现（唯一维护者）
- 文档状态机与发布控制

### 我必须保证的结果

1. 文档能够安全上传、解析、切分、索引、发布、更新和下线
2. 每个 Chunk 可追溯到原文、页码、标题和文档版本
3. 文档权限正确继承到 Chunk 和索引元数据
4. PostgreSQL、OpenSearch 和 pgvector 之间具有可重试、可检查的一致性机制
5. 文档更新能触发索引、缓存和标准问答联动

### 明确不属于我的主责

- 不负责查询端检索排序（成员6）
- 不负责 RRF、Reranker 和答案生成（成员6）
- 不负责标准问答审核逻辑（成员7）
- 不负责前端后台页面（成员2/3）
- 不自行定义权限规则，只消费成员4的权限结果
- 不实现第二套 Embedding 配置（我唯一维护，成员6只能复用）

---

## 2. 代码归属

### 我可以修改的文件

按照 README.md 定义的项目结构，成员5在以下范围内开发：

```text
backend/app/models/document.py      # 文档相关数据模型（KnowledgeBase/Document/DocumentVersion/DocumentChunk/IndexTask/DocumentProcessLog 等）
backend/app/schemas/document.py     # 文档相关 Schema
backend/app/api/knowledge_bases.py  # 知识库路由
backend/app/api/documents.py        # 文档路由
backend/app/api/chunks.py           # Chunk 路由
backend/app/api/index_tasks.py      # 索引任务路由（需新建）
backend/app/services/               # 业务服务（可新建知识库/文档/解析/切分/索引等服务）
backend/app/tasks/                  # Celery 任务（文档处理/索引写入/一致性检查）
backend/app/providers/              # Provider 实现（OCR/Embedding，需新建）
backend/tests/                      # 成员5相关测试
```

### 严格禁止修改的文件

```text
backend/app/models/user.py          # 成员4
backend/app/models/auth.py          # 成员4
backend/app/models/audit.py         # 成员4
backend/app/models/qa.py            # 成员7
backend/app/api/auth.py             # 成员4
backend/app/api/qa.py               # 成员7
backend/app/api/feedback.py         # 成员7
backend/app/core/                   # 成员1（需评审）
frontend/                           # 成员2/3
deploy/                             # 成员1+7
docs/                               # 成员1
```

公共目录（`core/`、`db/`、`utils/` 等）的改动必须先与成员1确认。

---

## 3. 技术栈与架构约束

### 后端

```text
Python 3.10、FastAPI、SQLAlchemy 2.x（Async）、Alembic
PostgreSQL（业务状态唯一事实来源）+ pgvector（向量索引）
OpenSearch（BM25 关键词索引）
Redis（缓存）、Celery（异步任务）、MinIO（原始文件存储）
```

### 解析与切分

```text
pdfplumber / PyMuPDF（PDF）、python-docx（DOCX）
markdown（Markdown）、BeautifulSoup（HTML）
```

### 关键架构原则

- PostgreSQL 是业务状态唯一事实来源，OpenSearch、pgvector 和缓存均为派生数据
- 跨模块事件通过数据库事务内 Outbox 传递，不引入额外消息队列
- 索引写入必须幂等（基于 idempotent_key）
- 只有已发布 + 当前版本 + 未过期 + 权限有效的文档可被成员6检索
- 新版本未准备完成前不得覆盖旧版本

---

## 4. 核心数据模型

### 必须实现的模型

```text
KnowledgeBase              # 知识库
KnowledgeBasePermission    # 知识库权限
Document                   # 文档
DocumentVersion            # 文档版本
DocumentPermission         # 文档权限
DocumentChunk              # 文档切分块
IndexTask                  # 索引任务
DocumentProcessLog         # 文档处理日志
```

### 模型层级关系

```text
KnowledgeBase
  └─ Document
      └─ DocumentVersion
          └─ DocumentChunk
              └─ IndexTask
```

### DocumentChunk 必须记录的字段

```text
tenant_id、knowledge_base_id、document_id、document_version_id
chunk_no、title_path、page_start、page_end、source_offset
raw_text、clean_text、token_count
metadata（JSON）、permission_metadata（JSON，继承自文档）
effective_time、expiration_time、status
```

### IndexTask 必须记录的字段

```text
task_type（create/update/delete/rebuild/consistency_check）
target（opensearch/pgvector）
document_version_id、chunk_id（可选）
idempotent_key、status、retry_count
error_message、created_at、completed_at
```

### 关键约束

- Chunk ID 必须稳定可追踪，文档版本变化后不得错误复用旧版本内容
- 索引写入必须幂等
- 同一文档版本不可重复产生冲突索引

---

## 5. 文档状态机

### 状态定义

```text
草稿（draft）
  -> 处理中（processing）
    -> 处理失败（failed）       [可回退到草稿重试]
    -> 待检查（pending_review）
      -> 待发布（pending_publish）
        -> 已发布（published）   [唯一可被成员6检索的状态]
          -> 已暂停（paused）
          -> 已过期（expired）
          -> 已下线（offline）   [立即从正式召回范围排除]
        -> 已归档（archived）    [保留历史，不参与检索]
```

### 关键规则

1. 解析和切分成功不等于已发布
2. 索引完成不等于已发布
3. 只有已发布 + 当前版本 + 未过期 + 权限有效的文档可被成员6检索
4. 下线后立即从正式召回范围排除
5. 归档用于保留历史，不参与检索

---

## 6. 文档版本更新流程

```text
1. 上传新版本文件
2. 创建新版本记录（不覆盖旧版本）
3. 解析和切分新版本
4. 比较新旧 Chunk 差异
5. 创建增量索引任务（新增/变更/删除）
6. 验证新索引可用性
7. 发布新版本（仅此时旧版本退出正式检索）
8. 旧版本退出正式检索范围
9. 通知成员6：缓存失效
10. 通知成员7：相关问答待复核
11. 记录审计日志
```

---

## 7. 索引写入核心规则

1. 索引写入必须幂等（基于 idempotent_key）
2. 失败可重试（retry_count 递增）
3. 同一文档版本不可重复产生冲突索引
4. 文档下线创建删除或失效任务
5. 提供索引重建脚本
6. 提供一致性检查脚本
7. OpenSearch 和 pgvector 都存储文档版本及权限元数据
8. 只有两种索引都达到可用状态，文档才具备发布条件

### 职责边界

```text
成员5：Embedding 任务和向量写入 + OpenSearch 文档写入
成员6：检索读取、融合和排序（只读）
```

---

## 8. API 契约

### 必须实现的端点

```text
# 知识库
POST   /api/v1/knowledge-bases                     # 创建知识库
GET    /api/v1/knowledge-bases                     # 知识库列表（分页+搜索+状态筛选）
GET    /api/v1/knowledge-bases/{id}                # 知识库详情
PUT    /api/v1/knowledge-bases/{id}                # 编辑知识库
PATCH  /api/v1/knowledge-bases/{id}/enable         # 启用
PATCH  /api/v1/knowledge-bases/{id}/disable        # 停用
GET    /api/v1/knowledge-bases/{id}/stats          # 统计

POST   /api/v1/knowledge-bases/{id}/permissions    # 配置权限
GET    /api/v1/knowledge-bases/{id}/permissions    # 查询权限

# 文档
POST   /api/v1/documents/upload                    # 单文件上传
POST   /api/v1/documents/batch-upload              # 批量上传
GET    /api/v1/documents                           # 文档列表
GET    /api/v1/documents/{id}                      # 文档详情
PATCH  /api/v1/documents/{id}/publish              # 发布
PATCH  /api/v1/documents/{id}/pause                # 暂停
PATCH  /api/v1/documents/{id}/offline              # 下线

GET    /api/v1/documents/{id}/versions             # 版本列表
GET    /api/v1/documents/{id}/versions/{vid}       # 版本详情

# Chunk
GET    /api/v1/document-chunks                     # Chunk列表
GET    /api/v1/document-chunks/{id}                # Chunk详情

# 索引任务
GET    /api/v1/index-tasks                         # 索引任务列表
GET    /api/v1/index-tasks/{id}                    # 索引任务详情
POST   /api/v1/index-tasks/{id}/retry              # 重试失败任务
POST   /api/v1/index-tasks/rebuild                 # 重建索引
POST   /api/v1/index-tasks/consistency-check       # 一致性检查
```

### API 通用要求

- 遵守公共响应格式：`success`、`data`、`error`、`request_id`
- 所有时间字段使用 ISO 8601 格式
- 分页统一使用 `page` + `page_size`（offset + limit）
- 所有端点提供：分页、搜索、状态筛选、处理进度、失败原因、权限校验、审计

---

## 9. 跨模块事件（Outbox）

### 我必须发出的事件

```text
document.version.created     # 新版本创建
document.version.published   # 新版本发布成功
document.paused              # 文档暂停
document.offlined            # 文档下线
document.permission.changed  # 权限变更
document.index.completed     # 索引完成
```

### Outbox 规则

1. 事件与文档状态变更在同一数据库事务中写入
2. 事件具有唯一 ID 和幂等键
3. 消费失败可以重试
4. 重复事件不得重复下线问答或重复清理索引
5. 只有新版本发布成功后才发出 `document.version.published`
6. 新版本构建失败时，旧版本继续保持可用

---

## 10. 跨模块依赖

### 我依赖成员4的接口

```text
PermissionService.get_access_context(tenant_id, user_id, resource_type, resource_id)
  -> 返回 AccessContext（含权限范围和 scope_hash）

PermissionService.check_permission(tenant_id, user_id, action, resource_type, resource_id)
  -> 返回 bool
```

在成员4接口可用之前，使用 Mock 实现，但字段结构必须与契约一致。

### 我提供给成员6的接口

```text
ChunkService.get_chunks_by_document_version(version_id, permission_context)
  -> 返回权限过滤后的 Chunk 列表

EmbeddingProvider.generate_vectors(texts, model_name)
  -> 返回向量列表（成员6用于查询向量生成）

IndexingService.get_index_status(document_version_id)
  -> 返回索引状态（opensearch + pgvector 双状态）
```

### 我提供给成员7的接口

```text
Outbox 事件：document.version.published / document.offlined 等
DocumentVersionService.get_current_version(document_id)
  -> 返回当前生效版本信息
```

---

## 11. Git 协作规范

### 分支

- 分支前缀：`feature/m5-`
- 当前分支：`feature/m5-document-pipeline`
- 目标分支：`develop`（禁止直接提交到 `main` 或 `develop`）

### 创建新分支

```bash
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feature/m5-<任务名>
```

### 日常提交

```bash
git status --short
git add <本次任务涉及的文件>
git diff --cached
git commit -m "<类型>(m5): <简明说明>"
git push -u origin <当前功能分支>
```

### Commit 类型

```text
feat     # 新功能
fix      # 修复 bug
refactor # 重构
test     # 测试
docs     # 文档
chore    # 构建/配置/工具
```

### 禁止事项

- 禁止直接向 `main` 或 `develop` 推送
- 禁止 `git push --force`、`git push -f`
- 禁止 `git reset --hard`、`git clean -fd`
- 禁止提交真实 `.env`、密钥、令牌、数据库数据、上传文件
- 禁止修改其他成员主责目录
- 禁止绕过 Pull Request 直接复制文件到集成分支

### 联调提醒

- 修改权限相关字段时，邀请成员4评审
- 修改索引相关接口时，邀请成员6评审
- 修改版本事件契约时，邀请成员7评审
- 修改公共目录时，需要成员1评审

---

## 12. 编码规范

### Python 代码风格

- 使用 type hints（Python 3.10 语法）
- 函数和关键逻辑必须添加中文注释
- 使用 Pydantic v2 进行请求/响应模型定义
- SQLAlchemy 2.x 声明式模型，使用 `Mapped` 和 `mapped_column`
- 异步数据库会话

### 配置管理

- 所有配置通过 `.env` 管理，禁止硬编码
- API Key、模型名称、数据库连接、MinIO 配置等必须在环境变量中
- 使用 `app.core.config.settings` 加载配置

### 错误处理

- 使用项目统一错误码体系（`app.core.exceptions`）
- 业务异常使用自定义 Exception 类
- 不使用裸 `raise Exception`
- 失败路径必须有明确错误信息和可重试机制

### 日志

- 结构化日志（JSON 格式），包含 `request_id` 和 `trace_id`
- 关键操作记录耗时指标
- 索引任务状态变更记录审计日志

---

## 13. 测试要求

### 必须覆盖的测试场景

| 类别 | 场景 |
|------|------|
| 文档格式 | PDF、DOCX、TXT、Markdown、HTML 每种格式解析 |
| 上传安全 | MIME 与扩展名不一致、重复上传、空文件、超大文件 |
| 扫描PDF | 无OCR 时的处理和标记 |
| 切分策略 | 标题切分、条款切分、表格切分、长段落二次切分 |
| 权限继承 | 知识库 -> 文档 -> Chunk -> 索引元数据权限继承 |
| 状态流转 | 解析失败重试、下线后不可检索 |
| 索引任务 | 幂等性、OpenSearch 写入失败、pgvector 写入失败 |
| 版本管理 | 版本更新、新旧版本切换、一致性检查和重建 |

### 测试样本必须包含

```text
公共文档、部门私有文档、已过期文档、多版本文档
包含编号、表格、日期的文档
```

---

## 14. 里程碑

### M1：知识库和上传

- 完善数据模型（补充所有缺失字段）
- 知识库 CRUD 实现
- MinIO 存储集成
- 文件上传与安全校验

### M2：解析与切分

- 一期格式解析（PDF/DOCX/TXT/Markdown/HTML）
- Chunk 切分（标题/章节/段落/条款/表格）
- 质量检查

### M3：索引与发布

- EmbeddingProvider 实现
- OpenSearch BM25 索引写入
- pgvector 向量索引写入
- IndexTask 任务管理
- 文档发布状态控制

### M4：版本联动

- 增量更新（新旧 Chunk 差异比对）
- 缓存失效通知（成员6）
- 问答待复核通知（成员7）
- 下线清理

### 验收标准

1. 文档全生命周期可运行
2. Chunk 可追溯到原文、页码、标题和版本
3. 权限正确继承到 Chunk 和索引元数据
4. 失败任务可重试
5. 索引写入幂等
6. 新版本不会破坏旧版本可用性
7. 文档下线后成员6无法召回
8. 相关问答进入待复核

---

## 15. 交付要求（14项清单）

每项功能交付时必须同时提供：

```text
1.  可运行的模块源代码
2.  数据库迁移脚本（Alembic）
3.  API 接口文档（端点、参数、响应、错误码）
4.  环境变量和配置说明
5.  单元测试
6.  关键接口集成测试
7.  结构化日志和监控指标
8.  权限校验说明
9.  模块 README
10. 演示数据或 Mock 数据
11. 验收清单（逐项通过记录）
12. 已知问题和技术债务清单
13. 已推送到功能分支，并创建以 develop 为目标分支的 Gitea PR
14. PR 中填写：测试结果、依赖关系、迁移说明、接口变更、联调要求
```

---

## 16. 工作约定

除上述项目规定外，本成员开发时还需遵守：

1. **不确定就问**：遇到不确定的内容（业务规则、接口字段、状态流转等），先向用户确认再动手，不自行猜测
2. **中文注释**：函数、关键逻辑、复杂算法必须添加中文注释，接口说明和文档统一使用简体中文
3. **完整覆盖**：每项功能对照任务书第2.1节（核心保证结果）、第13节（测试任务）、第15节（交付要求）逐项确认覆盖完整

---

## 17. 项目十条共同规则

1. 权限过滤必须在检索之前
2. PostgreSQL 中的业务状态是系统事实来源
3. 文档、Chunk、标准问答和引用必须保持权限与版本一致
4. 未审核的候选问答不得进入正式问答链路
5. 证据不足、证据冲突或无权限时不得生成确定性答案
6. 所有关键请求使用统一的 request_id 和 trace_id
7. API、错误码、状态枚举、分页格式和时间格式必须遵守公共规范
8. 每项功能必须同时提供代码、测试、接口说明、配置说明和验收记录
9. 禁止提交伪代码、固定返回值、核心逻辑空实现或绕过权限的临时代码
10. 页面、接口说明和项目文档统一使用简体中文，禁止使用 Emoji
