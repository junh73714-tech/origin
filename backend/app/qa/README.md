# 标准问答、评估与监控模块（成员7）

## 模块概述

本模块是成员7的主责模块，覆盖标准问答生命周期、知识运营、自动评估、监控指标和容器化部署支持。

### 子模块

| 子模块 | 目录 | 说明 |
|--------|------|------|
| 标准问答 | `backend/app/qa/` | 标准问答 CRUD、审核发布状态机、候选问答生成 |
| 评估模块 | `backend/app/evaluation/` | Golden Dataset、评估用例、评估运行、指标计算 |
| 监控模块 | `backend/app/monitoring/` | Prometheus 指标采集、Grafana 看板数据 |
| 异步任务 | `backend/app/tasks/` | 候选问答生成、质量检查、Outbox 事件消费、过期自动标记 |
| 部署支持 | `deploy/` | Docker Compose、Prometheus 配置、Grafana 看板 |

## 标准问答状态机

```
草稿 → 自动生成 → 待审核 → 审核驳回 → 待发布 → 已发布 → 待复核 → 已过期 → 已停用
```

## 核心 API

### 标准问答
- `POST /api/v1/qa/standard` - 创建标准问答
- `GET /api/v1/qa/standard` - 查询标准问答列表
- `GET /api/v1/qa/standard/{id}` - 获取标准问答详情
- `PUT /api/v1/qa/standard/{id}` - 更新标准问答
- `POST /api/v1/qa/standard/{id}/submit-review` - 提交审核
- `POST /api/v1/qa/reviews` - 提交审核结果
- `POST /api/v1/qa/standard/{id}/publish` - 发布
- `POST /api/v1/qa/standard/{id}/disable` - 停用
- `POST /api/v1/qa/match` - 标准问答匹配（供成员6调用）

### 候选问答
- `POST /api/v1/qa/candidates/generate` - 触发候选生成
- `GET /api/v1/qa/candidates` - 查询候选列表
- `POST /api/v1/qa/candidates/{id}/review` - 审核候选
- `POST /api/v1/qa/candidates/{id}/convert` - 转为标准问答

### 质量检查
- `POST /api/v1/qa/standard/{id}/quality-check` - 触发质量检查
- `GET /api/v1/qa/standard/{id}/quality-check` - 获取检查结果

### 反馈与运营
- `POST /api/v1/feedback/` - 提交反馈
- `GET /api/v1/feedback/` - 查询反馈列表
- `GET /api/v1/feedback/operations/unanswered` - 未命中问题
- `GET /api/v1/feedback/operations/high-frequency` - 高频问题
- `GET /api/v1/feedback/operations/low-quality` - 低质量答案
- `GET /api/v1/feedback/operations/knowledge-gaps` - 知识缺口

### 评估
- `POST /api/v1/evaluation/datasets` - 创建数据集
- `GET /api/v1/evaluation/datasets` - 查询数据集列表
- `POST /api/v1/evaluation/datasets/{id}/cases` - 添加评估用例
- `POST /api/v1/evaluation/runs` - 触发评估运行
- `GET /api/v1/evaluation/runs` - 查询评估运行列表

### 监控
- `GET /metrics` - Prometheus 指标端点

## 依赖关系

- **成员4**：权限上下文（roles、departments、data_scopes）
- **成员5**：文档、Chunk、EmbeddingProvider、文档版本事件
- **成员6**：检索调试接口、问答日志

## 验收标准

1. 候选问答绑定真实来源，未审核不能命中
2. 匹配同时考虑语义、关键词、实体、权限和版本
3. 文档更新使问答进入待复核
4. 高频与未命中问题可识别和处理
5. 评估可重复运行，检索、生成和权限指标可查看
6. 关键服务和任务可监控
7. Docker Compose 可在干净环境启动

## 环境变量

参考 `.env.example` 中的以下配置项：

- `LLM_API_KEY` / `LLM_BASE_URL` - LLM 调用的 API 密钥和地址
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` - Celery 消息队列和结果后端