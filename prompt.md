# 角色设定

你是一位资深全栈工程师，专注于企业级后端系统开发。你正在协助我完成一个**企业级混合检索 RAG 知识问答平台**项目中"成员7"所负责的全部模块开发。

请严格基于以下项目规范和任务书，为我逐步输出完整的、可运行的代码实现。所有代码必须使用简体中文注释，禁止使用 Emoji，禁止输出伪代码、固定返回值或空实现。

---

## 一、项目背景

本项目是一个企业级知识问答平台，七人团队分工协作，核心能力包括：

- 用户身份认证与 RBAC/ABAC 权限隔离
- 知识库、文档、版本、Chunk 与索引管理
- Keyword Retrieval（OpenSearch）与 Vector Retrieval（pgvector）
- 混合检索、RRF 融合与 Reranker
- 基于证据的 RAG 问答、拒答和来源引用
- **标准问答生成、审核、发布、失效与版本联动（我负责）**
- **用户反馈、知识缺口发现与效果评估（我负责）**
- **查询日志、Prometheus 监控、Grafana 看板与 Docker 容器化部署（我负责）**

## 二、统一技术栈

| 层级 | 技术 |
|------|------|
| 后端语言 | Python 3.10 |
| 后端框架 | FastAPI |
| ORM | SQLAlchemy 2.x |
| 数据库迁移 | Alembic |
| 主数据库 | PostgreSQL（业务状态唯一事实来源） |
| 向量检索 | pgvector |
| 关键词检索 | OpenSearch |
| 缓存 | Redis |
| 异步任务 | Celery |
| RAG 编排 | LangGraph |
| 对象存储 | MinIO |
| 前端 | React + TypeScript + Vite + Ant Design |
| 部署 | Docker Compose |
| 监控 | Prometheus + Grafana |

### 关键架构约束

- PostgreSQL 是业务状态的唯一事实来源，OpenSearch、pgvector 和缓存均为派生数据
- 跨模块状态变化通过数据库事务内写入的 Outbox 事件传递，不额外引入消息队列
- 权限过滤必须发生在检索之前
- 未审核的候选问答不得进入正式问答链路
- 所有关键请求使用统一的 `request_id` 和 `trace_id`

## 三、我的角色：成员7 -- 问答优化、评估与平台工程负责人

### 3.1 核心职责

1. **标准问答生命周期**：候选问答生成、自动质量检查、审核发布状态机、标准问答匹配服务
2. **用户反馈与知识运营**：点赞/点踩、纠错、未命中问题、高频问题、知识缺口识别
3. **评估体系**：Golden Dataset 管理、自动评估（检索/生成/权限指标）
4. **监控与部署**：Prometheus 指标采集、Grafana 看板、Docker Compose 容器化

### 3.2 我不负责的内容

- 不负责总体架构和最终版本决策（成员1）
- 不负责文档解析和 Chunk 生成（成员5）
- 不负责正式混合检索和答案生成（成员6）
- 不负责权限规则定义（成员4）
- 不负责后台页面实现（成员3），只提供后端接口与数据

### 3.3 代码归属目录

```
backend/app/qa/                    # 标准问答模块
backend/app/evaluation/            # 评估模块
backend/app/monitoring/            # 监控模块
backend/app/tasks/evaluation/      # 评估异步任务
backend/tests/qa/                  # 标准问答测试
backend/tests/evaluation/          # 评估测试
deploy/prometheus/                 # Prometheus 配置
deploy/grafana/                    # Grafana 配置与看板
deploy/docker-compose*.yml         # Docker Compose 编排文件
```

---

## 四、实施顺序（严格按此顺序）

### M1：标准问答闭环

#### 4.1 标准问答数据模型

至少实现以下实体（使用 SQLAlchemy 2.x 声明式模型）：

- `StandardQuestion`：标准问题（问题文本、关键词、核心实体、适用范围、状态、版本）
- `StandardAnswer`：标准答案（简短答案、详细答案、来源绑定）
- `QuestionVariant`：相似问法（多个相似问句绑定到一个标准问题）
- `QAReviewRecord`：审核记录（审核人、审核动作、审核意见、时间）
- `QASource`：来源绑定（来源文档 ID、文档版本、Chunk ID、知识库 ID）
- `QAQualityCheck`：质量检查结果（检查项、检查结果、检查时间）

每个标准问答必须绑定：来源文档、来源文档版本、来源 Chunk、适用知识库、适用角色、适用部门、生效时间、失效时间、审核人、审核时间、状态、版本。

**标准问答不得拥有比来源文档更大的访问范围。**

#### 4.2 审核与发布状态机

状态流转：

```
草稿 → 自动生成 → 待审核 → 审核驳回
                          → 待发布 → 已发布 → 待复核
                                            → 已过期
                                            → 已停用
```

审核动作：通过、驳回、返回修改、发布、暂停、停用、标记重复、标记来源文档问题。

发布前必须校验：来源有效、权限有效、必要条件完整、审核通过、生效时间合理、未与现有问答冲突。

#### 4.3 候选问答生成（Celery 异步任务）

消费成员5提供的有效文档和 Chunk，生成：
- 候选问题、标准答案、简短答案、详细答案
- 相似问法（至少3条）
- 关键词、核心实体
- 适用范围建议
- 来源文档和 Chunk 绑定
- 生成模型和提示词版本号

要求：每个答案可追溯来源；可批量执行；失败可重试；重复内容可识别；候选内容不得自动发布；标记为机器生成。

#### 4.4 自动质量检查

检查项（至少10项）：
1. 答案是否由来源支持
2. 是否超出原文
3. 问题和答案是否匹配
4. 是否缺少时间、地区、岗位等条件
5. 是否与已有问答重复
6. 是否包含敏感信息
7. 是否扩大权限
8. 来源文档是否有效
9. 来源版本是否当前
10. 答案是否使用绝对化但无依据的表述

自动检查结果只能辅助审核，不替代人工审核。

#### 4.5 标准问答匹配服务（提供给成员6调用）

输入：
```python
{
    "query": "用户问题",
    "keywords": [],
    "entities": [],
    "intent": "",
    "access_context": {},  # 来自成员4的权限上下文
    "knowledge_base_ids": []
}
```

输出：
```python
{
    "matched": True,
    "qa_id": "",
    "answer": "",
    "variants": [],
    "semantic_score": 0.0,
    "keyword_score": 0.0,
    "entity_consistency": 0.0,
    "scope_consistency": 0.0,
    "final_score": 0.0,
    "citations": [],
    "status": "",
    "reason": ""
}
```

匹配条件（全部满足才可命中）：已审核、已发布、未过期、来源文档有效、权限一致、角色和部门适用、核心实体一致、综合评分达到阈值。相似度高但实体/时间/适用范围不一致时不得直接命中。

**Embedding 复用**：语义匹配必须复用成员5提供的 `EmbeddingProvider`，不得创建第二套语义空间。

#### 4.6 文档版本联动

消费成员5的 Outbox 事件：
- `document.version.published`
- `document.paused`
- `document.offlined`
- `document.permission.changed`

处理逻辑（必须幂等）：
1. 找到受影响问答
2. 标记待复核
3. 下线无效问答
4. 更新来源版本
5. 记录原因
6. 通知运营人员
7. 触发相关评估样本重跑
8. 通知成员6缓存失效

### M2：知识运营闭环

#### 4.7 用户反馈

实现接口：
- 点赞 / 点踩
- 纠错说明提交
- 反馈列表查询（分页、筛选）

#### 4.8 知识运营分析

- **未命中问题**：识别用户提问但未命中标准问答且 RAG 拒答或低质量回答的情况
- **高频问题**：按时间窗口统计高频查询
- **低质量答案**：基于用户点踩和引用质量识别
- **相似问题聚类**：对未命中和高频问题进行语义聚类
- **知识缺口任务**：来源包括高频拒答、多次改写仍未命中、用户集中点踩、同一问题冲突答案、某部门高频询问但无正式文档

不得自动把用户问题转成已发布知识，必须进入运营或审核流程。

### M3：评估闭环

#### 4.9 Golden Dataset

每条样本包含：标准问题、标准答案、标准文档、标准 Chunk、允许角色、禁止角色、是否应拒答、问题类型、难度等级、核心实体、时间和地区条件。

数据集版本化：创建人、版本、变更说明、状态、适用配置。

#### 4.10 自动评估任务

**检索指标**：Recall@K、Precision@K、MRR、NDCG、标准文档命中率、标准 Chunk 命中率、Keyword 召回率、Vector 召回率、混合检索提升率、Reranker 提升率

**生成指标**：Faithfulness、Answer Relevance、Context Relevance、引用准确率、引用完整率、无答案识别率、错误拒答率、幻觉率

**权限指标**：越权召回、越权引用、越权回答、跨权限缓存泄露、下线文档命中、过期文档命中

**正式验收目标**：越权召回 = 0、越权引用 = 0、越权回答 = 0、跨权限缓存泄露 = 0

评估任务必须通过成员6的正式检索/问答/调试接口执行，不得绕过权限。评估运行需保存：数据集版本、测试 AccessContext、检索参数、模型版本、提示词版本、代码版本、起止时间、失败样本。支持重复运行、历史对比、失败重试、结果导出。

### M4：监控与部署

#### 4.11 Prometheus 指标

与成员1统一命名，至少采集：API 请求量、API 错误率、P50/P95、LLM 调用量和耗时、Token 使用量、Embedding 调用量、Reranker 耗时、Keyword/Vector 检索耗时、文档处理成功率、索引任务成功率、标准问答命中率、拒答率、用户反馈统计、Celery 队列长度、关键服务健康状态。

**指标采集责任边界**：成员7负责指标注册规范检查、Prometheus 抓取配置、Grafana 看板、告警规则和运行说明。不得通过解析普通文本日志代替业务模块的正式指标埋点。

#### 4.12 Grafana 看板

至少包括6个 Dashboard：
1. 系统总览
2. RAG 链路性能
3. 文档与索引任务
4. 模型调用与成本
5. 标准问答与用户反馈
6. 安全与权限事件

#### 4.13 Docker Compose 部署

与成员1协作，包含：后端 Dockerfile、前端 Dockerfile、Worker Dockerfile、Docker Compose（含 PostgreSQL、OpenSearch、Redis、MinIO、Prometheus、Grafana、Nginx）、健康检查、持久化卷、初始化脚本、备份恢复说明。

---

## 五、主要 API 清单

### 标准问答

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/qa/candidates` | 触发候选问答生成任务 |
| GET | `/api/v1/qa/candidates` | 查询候选问答列表 |
| POST | `/api/v1/qa/reviews` | 提交审核结果 |
| GET | `/api/v1/qa/reviews` | 查询审核记录 |
| GET | `/api/v1/qa/standard` | 查询已发布标准问答列表 |
| POST | `/api/v1/qa/match` | 标准问答匹配（供成员6调用） |
| POST | `/api/v1/qa/{id}/publish` | 发布标准问答 |
| POST | `/api/v1/qa/{id}/disable` | 停用标准问答 |

### 反馈和运营

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/feedback` | 提交用户反馈 |
| GET | `/api/v1/operations/unanswered` | 查询未命中问题 |
| GET | `/api/v1/operations/high-frequency` | 查询高频问题 |
| GET | `/api/v1/operations/low-quality` | 查询低质量答案 |
| GET | `/api/v1/operations/knowledge-gaps` | 查询知识缺口任务 |

### 评估

| 方法 | 路径 | 说明 |
|------|------|------|
| POST/GET | `/api/v1/evaluation/datasets` | 管理 Golden Dataset |
| GET | `/api/v1/evaluation/cases` | 查询评估用例 |
| POST | `/api/v1/evaluation/runs` | 触发评估运行 |
| GET | `/api/v1/evaluation/runs/{id}` | 查询评估运行结果 |

---

## 六、Git 协作规范

- 分支前缀：`feature/m7-`
- Commit 格式：`<类型>(m7): <简明说明>`，类型包括 `feat`、`fix`、`refactor`、`test`、`docs`、`chore`
- 每个子任务创建独立分支，PR 目标为 `develop`
- 禁止直接向 `main` 或 `develop` 推送
- 禁止 `git push --force`
- 禁止提交真实 `.env`、密钥、令牌

---

## 七、交付要求

每个模块必须同时提交：
1. 可运行的模块源代码
2. Alembic 数据库迁移脚本
3. API 接口文档
4. 环境变量和配置说明
5. 单元测试（`backend/tests/qa/` 和 `backend/tests/evaluation/`）
6. 关键接口集成测试
7. 结构化日志和监控指标
8. 权限校验说明
9. 模块 README
10. 演示数据或 Mock 数据
11. 验收清单

---

## 八、测试用例要求

### 标准问答测试
- 未审核不得命中
- 已发布可命中
- 过期不得命中
- 待复核不得命中
- 来源文档下线后问答自动待复核
- 权限不一致不得命中
- 高语义相似但实体不一致不得命中
- 文档版本变化触发复核
- 重复问答识别

### 评估测试
- 指标计算正确性
- 数据集版本管理
- 批量任务重试
- 配置对比
- 权限样本测试
- 应拒答样本测试

### 部署和监控测试
- Docker Compose 完整启动
- 健康检查通过
- Prometheus 正常抓取指标
- Grafana 数据源连接
- Celery Worker 任务执行
- 持久化卷验证
- 备份恢复演练

---

## 九、输出要求

请按 M1 → M2 → M3 → M4 的顺序，为每个里程碑输出：

1. **数据模型定义**：完整的 SQLAlchemy 模型代码
2. **Alembic 迁移脚本**：数据库变更
3. **Pydantic Schema**：请求和响应模型
4. **Service 层**：完整业务逻辑实现
5. **Celery 任务**：异步任务定义
6. **FastAPI Router**：API 路由和端点
7. **测试代码**：单元测试和集成测试
8. **配置文件**：Prometheus、Grafana、Docker Compose

所有代码必须完整可运行，不得省略核心逻辑。如果单次输出长度受限，请告诉我"继续"即可接续输出。

请从 **M1：标准问答闭环** 开始，首先输出数据模型（SQLAlchemy 模型）和状态机的完整实现。


