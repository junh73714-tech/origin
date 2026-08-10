# M4 评估、安全、设置页面 - 契约文件

## 概述
- **里程碑**: M4 - 评估中心、安全审计、系统设置
- **分支**: `feature/m3-admin-pages-3`
- **成员**: 成员3
- **日期**: 2026-07-16
- **状态**: 已完成

## 已实现页面（4个）

### 评估任务 (EvalTasks)
- 创建评估任务、查看进度和评估指标（MRR/NDCG/BLEU/Faithfulness）
- 失败重试入口

### 安全事件 (SecurityEvents)
- 5种事件类型：越权访问、提示词注入、暴力破解、异常登录、数据泄露
- 4级严重级别：low/medium/high/critical
- 标记已处理

### 操作日志 (OperationLogs)
- 8种操作类型：创建、更新、删除、查看、登录、登出、发布、审核
- 按用户/操作筛选、Trace ID追踪

### 系统健康 (SystemHealth)
- 5个组件：PostgreSQL、Redis、OpenSearch、MinIO、Celery
- CPU/内存/磁盘使用率监控

## 验收状态
- [x] 4个页面实现
- [x] 构建通过
- [x] 已推送
- [ ] API 联调
- [ ] 集成测试