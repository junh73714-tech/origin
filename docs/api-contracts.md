# API 契约文档

## 1. 概述

### 1.1 API 版本
当前版本：`v1`
基础路径：`/api/v1`

### 1.2 认证方式
使用 JWT Bearer Token 认证。
- Access Token：短期令牌，有效期 30 分钟
- Refresh Token：长期令牌，有效期 7 天

### 1.3 请求格式
- Content-Type: `application/json`
- 请求头必须包含：`Authorization: Bearer <token>`

### 1.4 响应格式

#### 成功响应
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "request_id": "req_123456789"
}
```

#### 失败响应
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  },
  "request_id": "req_123456789"
}
```

#### 分页响应
```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "message": "查询成功",
  "request_id": "req_123456789"
}
```

## 2. 认证接口

### 2.1 登录
```
POST /api/v1/auth/login
```

**请求体：**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "string",
      "email": "string",
      "username": "string",
      "full_name": "string",
      "is_active": true,
      "is_superuser": false,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    },
    "tokens": {
      "access_token": "string",
      "refresh_token": "string",
      "token_type": "bearer",
      "expires_in": 1800
    }
  }
}
```

### 2.2 注册
```
POST /api/v1/auth/register
```

**请求体：**
```json
{
  "email": "user@example.com",
  "username": "string",
  "password": "string",
  "full_name": "string"
}
```

### 2.3 刷新令牌
```
POST /api/v1/auth/refresh
```

**请求体：**
```json
{
  "refresh_token": "string"
}
```

### 2.4 登出
```
POST /api/v1/auth/logout
```

### 2.5 获取当前用户
```
GET /api/v1/auth/me
```

## 3. 知识库接口

### 3.1 创建知识库
```
POST /api/v1/knowledge-bases
```

**请求体：**
```json
{
  "name": "string",
  "description": "string",
  "icon": "string",
  "is_public": false,
  "settings": {}
}
```

### 3.2 获取知识库列表
```
GET /api/v1/knowledge-bases
```

**查询参数：**
- `page`: 页码 (默认 1)
- `page_size`: 每页数量 (默认 20, 最大 100)
- `keyword`: 搜索关键词

### 3.3 获取知识库详情
```
GET /api/v1/knowledge-bases/{kb_id}
```

### 3.4 更新知识库
```
PUT /api/v1/knowledge-bases/{kb_id}
```

### 3.5 删除知识库
```
DELETE /api/v1/knowledge-bases/{kb_id}
```

### 3.6 获取知识库统计
```
GET /api/v1/knowledge-bases/{kb_id}/stats
```

## 4. 文档接口

### 4.1 上传文档
```
POST /api/v1/knowledge-bases/{kb_id}/documents/upload
Content-Type: multipart/form-data

file: <binary>
```

**响应：**
```json
{
  "success": true,
  "data": {
    "document_id": "string",
    "name": "string",
    "file_type": "pdf",
    "file_size": 1024000,
    "status": "pending"
  }
}
```

### 4.2 获取文档列表
```
GET /api/v1/knowledge-bases/{kb_id}/documents
```

### 4.3 获取文档详情
```
GET /api/v1/documents/{document_id}
```

### 4.4 删除文档
```
DELETE /api/v1/documents/{document_id}
```

### 4.5 获取文档版本列表
```
GET /api/v1/documents/{document_id}/versions
```

### 4.6 获取文档 Chunk 列表
```
GET /api/v1/documents/{document_id}/chunks
```

## 5. 问答接口

### 5.1 发送消息
```
POST /api/v1/qa/chat
```

**请求体：**
```json
{
  "conversation_id": "string (可选)",
  "content": "string"
}
```

**响应 (SSE)：**
```
Content-Type: text/event-stream

event: message
data: {"content": "partial content", "done": false}

event: message
data: {"content": "complete answer", "done": true, "references": [...]}

event: done
data: {"conversation_id": "string", "message_id": "string"}
```

### 5.2 获取标准问答列表
```
GET /api/v1/qa/standard
```

**查询参数：**
- `page`, `page_size`: 分页
- `status`: 状态 (draft/published/unpublished)
- `category`: 分类

### 5.3 创建标准问答
```
POST /api/v1/qa/standard
```

**请求体：**
```json
{
  "knowledge_base_id": "string",
  "question": "string",
  "answer": "string",
  "keywords": ["string"],
  "category": "string",
  "priority": 0
}
```

### 5.4 发布标准问答
```
POST /api/v1/qa/standard/{qa_id}/publish
```

### 5.5 下线标准问答
```
POST /api/v1/qa/standard/{qa_id}/unpublish
```

### 5.6 获取会话列表
```
GET /api/v1/qa/conversations
```

### 5.7 获取会话详情
```
GET /api/v1/qa/conversations/{conversation_id}
```

## 6. 反馈接口

### 6.1 提交反馈
```
POST /api/v1/feedback
```

**请求体：**
```json
{
  "message_id": "string",
  "feedback": "positive | negative",
  "comment": "string",
  "score": 5
}
```

## 7. 公共接口

### 7.1 健康检查
```
GET /api/v1/health
```

### 7.2 就绪检查
```
GET /api/v1/ready
```

### 7.3 存活检查
```
GET /api/v1/live
```

## 8. ID 格式规范

| 资源类型 | ID 格式 | 示例 |
|----------|---------|------|
| 用户 ID | uuid | `usr_01HXYZ1234567890` |
| 租户 ID | uuid | `tnt_01HXYZ1234567890` |
| 知识库 ID | uuid | `kb_01HXYZ1234567890` |
| 文档 ID | uuid | `doc_01HXYZ1234567890` |
| 问答 ID | uuid | `qa_01HXYZ1234567890` |
| 会话 ID | uuid | `cnv_01HXYZ1234567890` |
| 消息 ID | uuid | `msg_01HXYZ1234567890` |

## 9. 时间格式

所有时间使用 ISO 8601 格式：
- 存储：UTC 时间
- 显示：根据客户端 locale 转换

示例：`2024-01-01T00:00:00Z`

## 10. 文件上传规范

| 参数 | 说明 |
|------|------|
| 最大文件大小 | 100MB |
| 支持格式 | pdf, docx, doc, xlsx, xls, pptx, ppt, txt, md, html, htm |
| Content-Type | multipart/form-data |
| 字段名 | file |
