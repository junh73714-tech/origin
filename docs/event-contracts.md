# 事件契约文档

## 1. 概述

本项目使用 Outbox 模式实现跨模块事件传递。所有跨模块状态变化通过数据库事务内的 Outbox 事件记录，确保最终一致性。

## 2. 事件信封格式

```json
{
  "event_id": "evt_01HXYZ1234567890",
  "event_type": "document.created",
  "aggregate_type": "document",
  "aggregate_id": "doc_01HXYZ1234567890",
  "tenant_id": "tnt_01HXYZ1234567890",
  "payload": {
    "document_id": "doc_01HXYZ1234567890",
    "knowledge_base_id": "kb_01HXYZ1234567890",
    "name": "产品手册.pdf",
    "file_type": "pdf",
    "created_by": "usr_01HXYZ1234567890"
  },
  "metadata": {
    "request_id": "req_123456789",
    "trace_id": "trace_123456789"
  },
  "occurred_at": "2024-01-01T00:00:00Z"
}
```

## 3. 事件类型定义

### 3.1 文档事件

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| `document.created` | 文档创建 | 文档上传成功 |
| `document.updated` | 文档更新 | 文档内容更新 |
| `document.deleted` | 文档删除 | 文档删除 |
| `document.status_changed` | 状态变更 | 处理状态变更 |
| `document.version_created` | 新版本创建 | 上传新版本 |

### 3.2 知识库事件

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| `knowledge_base.created` | 知识库创建 | 创建知识库 |
| `knowledge_base.updated` | 知识库更新 | 更新知识库 |
| `knowledge_base.deleted` | 知识库删除 | 删除知识库 |

### 3.3 问答事件

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| `qa.created` | 问答创建 | 创建标准问答 |
| `qa.updated` | 问答更新 | 更新标准问答 |
| `qa.published` | 问答发布 | 发布标准问答 |
| `qa.unpublished` | 问答下线 | 下线标准问答 |
| `qa.deleted` | 问答删除 | 删除标准问答 |
| `candidate_qa.created` | 候选问答创建 | AI 生成或用户提交 |
| `candidate_qa.approved` | 候选问答通过 | 审核通过 |
| `candidate_qa.rejected` | 候选问答拒绝 | 审核拒绝 |

### 3.4 索引事件

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| `index.started` | 索引开始 | 开始索引任务 |
| `index.progress` | 索引进度 | 索引进度更新 |
| `index.completed` | 索引完成 | 索引任务完成 |
| `index.failed` | 索引失败 | 索引任务失败 |

### 3.5 检索事件

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| `retrieval.query` | 检索查询 | 用户发起查询 |
| `retrieval.result` | 检索结果 | 返回检索结果 |

### 3.6 会话事件

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| `conversation.created` | 会话创建 | 创建新会话 |
| `conversation.message` | 新消息 | 发送消息 |

### 3.7 反馈事件

| 事件类型 | 说明 | 触发时机 |
|----------|------|----------|
| `feedback.positive` | 正面反馈 | 用户点赞 |
| `feedback.negative` | 负面反馈 | 用户点踩 |

## 4. 事件消费者

### 4.1 文档事件 -> 索引服务

```python
class DocumentEventConsumer:
    """处理文档相关事件"""

    def handle_document_created(self, event: OutboxEvent):
        """触发文档索引"""
        document_id = event.payload["document_id"]
        # 触发异步索引任务
        index_document.delay(document_id)

    def handle_document_deleted(self, event: OutboxEvent):
        """删除文档索引"""
        document_id = event.payload["document_id"]
        # 从索引中删除
        delete_document_index.delay(document_id)

    def handle_document_version_created(self, event: OutboxEvent):
        """触发新版本索引"""
        document_id = event.payload["document_id"]
        version = event.payload["version"]
        # 删除旧版本索引，创建新版本索引
        reindex_document_version.delay(document_id, version)
```

### 4.2 知识库事件 -> 缓存服务

```python
class KnowledgeBaseEventConsumer:
    """处理知识库相关事件"""

    def handle_knowledge_base_deleted(self, event: OutboxEvent):
        """清理知识库相关缓存"""
        kb_id = event.payload["knowledge_base_id"]
        # 清理缓存
        cache.delete(f"kb:{kb_id}")
        cache.delete(f"kb:{kb_id}:stats")
```

### 4.3 问答事件 -> 缓存服务

```python
class QAEventConsumer:
    """处理问答相关事件"""

    def handle_qa_published(self, event: OutboxEvent):
        """更新问答缓存"""
        qa_id = event.payload["qa_id"]
        # 刷新问答缓存
        refresh_qa_cache.delay(qa_id)

    def handle_qa_unpublished(self, event: OutboxEvent):
        """从缓存移除问答"""
        qa_id = event.payload["qa_id"]
        # 删除问答缓存
        cache.delete(f"qa:{qa_id}")

    def handle_candidate_qa_approved(self, event: OutboxEvent):
        """创建标准问答后触发"""
        qa_id = event.payload["standard_qa_id"]
        # 刷新候选问答列表
        cache.delete("candidate_qas:pending")
```

### 4.4 反馈事件 -> 评估服务

```python
class FeedbackEventConsumer:
    """处理反馈事件"""

    def handle_feedback_negative(self, event: OutboxEvent):
        """分析负面反馈"""
        message_id = event.payload["message_id"]
        # 分析原因，更新检索参数
        analyze_negative_feedback.delay(message_id)
```

## 5. 幂等性保证

所有事件消费者必须实现幂等处理：

```python
def handle_event(self, event: OutboxEvent):
    """处理事件，支持幂等"""
    processed_key = f"processed:{event.event_id}"

    # 检查是否已处理
    if cache.exists(processed_key):
        logger.info("event_already_processed", event_id=event.event_id)
        return

    # 处理业务逻辑
    self._process_event(event)

    # 标记已处理
    cache.setex(processed_key, 86400, "1")  # 24小时过期
```

## 6. 错误处理与重试

### 6.1 重试策略

| 重试次数 | 延迟 |
|----------|------|
| 1 | 1 秒 |
| 2 | 5 秒 |
| 3 | 30 秒 |

### 6.2 死信处理

超过最大重试次数后，将事件移入死信队列：

```python
if event.retry_count >= event.max_retries:
    # 移入死信队列
    dlq.publish(event)
    # 记录安全事件
    security_event = SecurityEvent(
        event_type="outbox_event_failed",
        severity="high",
        details={"event_id": event.id, "error": event.error_message}
    )
```

## 7. Outbox 事件表

```sql
CREATE TABLE outbox_events (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB,
    occurred_at TIMESTAMP NOT NULL,
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(64) NOT NULL,
    updated_by VARCHAR(64),
    CONSTRAINT chk_occurred_at CHECK (occurred_at <= NOW() + INTERVAL '1 day')
);

CREATE INDEX ix_outbox_events_unpublished ON outbox_events (published, created_at);
CREATE INDEX ix_outbox_events_aggregate ON outbox_events (aggregate_type, aggregate_id);
```
