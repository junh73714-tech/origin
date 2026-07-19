# 成员6 模块说明

## 1. 范围

混合检索、RAG 问答图、会话/SSE、引用、查询缓存、QueryLog/RetrievalLog/Citation。

## 2. API（以 api-contracts 为准）

- `POST /api/v1/qa/chat`（SSE）
- `GET /api/v1/qa/conversations`
- `GET /api/v1/qa/conversations/{id}`
- `GET /api/v1/qa/citations/{citation_id}`
- `POST /api/v1/qa/queries/{query_id}/cancel`
- `POST /api/v1/qa/debug/query`（后台调试，需权限）

扩展 SSE 事件：`message_start` / `answer_delta` / `citation` / `metadata` / `error` / `done`；公共契约中的 `message`+`done` 仍保留。

## 3. 数据模型新增

迁移 `002_m6_retrieval_logs`：`citations`、`query_logs`、`retrieval_logs`。

## 4. 环境变量（仅名称）

| 变量 | 用途 | 必填 |
|------|------|------|
| `OPENAI_*` / `APP_*` LLM 相关 | LLM 绑定 | 生产必填 |
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` | 向量维度一致性 | 是 |
| `RERANKER_PROVIDER` / `RERANKER_MODEL` / `RERANKER_TOP_N` | 重排 | 生产必填 |
| `OPENSEARCH_*` | Keyword 检索 | 集成必填 |
| `DATABASE_*` | pgvector | 集成必填 |
| `REDIS_*` | 缓存（当前进程内可运行） | 可选 |

## 5. 缓存键

必须包含：tenant_id、scope_hash、知识库范围、文档版本摘要、标准问答版本、问题摘要、LLM/Embedding/Reranker/提示词版本。

## 6. 跨模块联调

- 成员4：正式 PermissionService / scope_hash
- 成员5：正式 EmbeddingProvider 与索引写入
- 成员7：正式标准问答匹配服务
- 成员2：SSE 消费
- 成员3：debug 接口
- 成员1：路由别名、BaseModel.id、迁移、契约评审

## 7. 已知阻塞

1. 真实 LLM / Reranker 未绑定（当前 Mock，is_mock=True）
2. 成员4/5/7 正式服务未合入，使用适配器与测试替身
3. 会话/QueryLog/Citation 当前为进程内存储（结构已对齐表模型）；生产需切换 SQLAlchemy 写库
4. OpenSearch/pgvector 生产客户端需接成员5索引；API 默认空内存索引用于联调替身
