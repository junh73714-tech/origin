## 任务来源
成员编号：成员6
任务书章节：混合检索 / LangGraph RAG / 会话引用缓存
关联 Issue：

## 完成内容
- 权限感知 Keyword / Vector / 混合检索与 RRF
- LangGraph 风格正式问答图、标准问答适配、证据覆盖、引用二次鉴权
- SSE 会话接口、查询取消、调试接口、scope_hash 缓存隔离与事件幂等失效
- Citation / QueryLog / RetrievalLog 模型与迁移 002
- 定向单元测试 19 项通过

## 修改范围
- `backend/app/retrieval/`、`rag/`、`conversation/`、`providers/`、`prompts/`、`cache/query/`
- `backend/app/api/qa.py`、`models/retrieval_logs.py`、迁移与文档
- 公共最小改动：BaseModel.id、路由别名、AccessContext 扩展、config 注解（需成员1评审）

## 接口或数据模型变化
- 新增/完善 `/api/v1/qa/chat` SSE、conversations、citations、cancel、debug
- 新增表：citations、query_logs、retrieval_logs

## 数据库迁移
有：`002_m6_retrieval_logs.py`，支持 upgrade/downgrade

## 环境变量变化
有（仅名称）：`QUERY_CACHE_TTL_SECONDS`、`RETRIEVAL_RRF_K`、`RETRIEVAL_TOP_K`、`RETRIEVAL_TOKEN_BUDGET`、`RETRIEVAL_ALLOW_PARTIAL_DEGRADE`、`OPENSEARCH_CHUNK_INDEX`

## 测试
执行命令：`cd backend && pytest tests/retrieval tests/rag -v`
测试结果：19 passed

## 联调要求
依赖模块：成员4 PermissionService、成员5 Embedding/索引、成员7 标准问答匹配、真实 LLM/Reranker
需要谁参与：成员1、2、3、4、5、7

## 风险与回滚
风险：真实服务未绑定，当前使用 Mock/适配器；会话默认内存存储
回滚方式：`git revert` 本分支提交；`alembic downgrade 001`

## 检查
- [x] 未提交真实 .env、密码、密钥、Token、数据和构建产物
- [x] 未直接修改其他成员主责核心业务逻辑
- [x] 接口文档已同步（草案，待成员1签收）
- [x] 数据库迁移可升级和回退
- [x] 定向测试通过
- [ ] 已同步最新 develop（推送时网络不可达，需重试）
- [x] 权限默认拒绝与显式拒绝优先已验证
