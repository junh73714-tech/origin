# 错误码文档

## 1. 错误码规范

### 1.1 错误码格式
```
<分类>_<序号>
```

| 分类 | 前缀 | 说明 |
|------|------|------|
| 认证 | AUTH | 认证相关错误 |
| 授权 | AUTHZ | 权限相关错误 |
| 资源 | RES | 资源相关错误 |
| 验证 | VAL | 数据验证错误 |
| 状态 | STATE | 业务状态错误 |
| 业务 | BIZ | 业务逻辑错误 |
| 系统 | SYS | 系统错误 |
| 外部 | EXT | 外部服务错误 |

### 1.2 HTTP 状态码映射

| 错误码分类 | HTTP 状态码 |
|------------|-------------|
| AUTH | 401 Unauthorized |
| AUTHZ | 403 Forbidden |
| RES | 404 Not Found |
| VAL | 422 Unprocessable Entity |
| STATE | 409 Conflict |
| BIZ | 400 Bad Request |
| SYS | 500 Internal Server Error |
| EXT | 502 Bad Gateway |

## 2. 认证错误 (AUTH_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| AUTH_INVALID_CREDENTIALS | 401 | 用户名或密码错误 | 检查用户名和密码 |
| AUTH_TOKEN_EXPIRED | 401 | 令牌已过期 | 刷新令牌或重新登录 |
| AUTH_TOKEN_INVALID | 401 | 令牌无效 | 重新获取令牌 |
| AUTH_TOKEN_MISSING | 401 | 缺少令牌 | 在请求头添加 Authorization |
| AUTH_REFRESH_TOKEN_EXPIRED | 401 | 刷新令牌已过期 | 重新登录 |
| AUTH_USER_INACTIVE | 401 | 用户已被禁用 | 联系管理员 |
| AUTH_USER_NOT_FOUND | 404 | 用户不存在 | 检查用户名 |
| AUTH_EMAIL_EXISTS | 409 | 邮箱已被注册 | 使用其他邮箱 |
| AUTH_USERNAME_EXISTS | 409 | 用户名已被使用 | 使用其他用户名 |
| AUTH_WEAK_PASSWORD | 400 | 密码强度不足 | 使用更强的密码 |

## 3. 授权错误 (AUTHZ_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| AUTHZ_PERMISSION_DENIED | 403 | 权限不足 | 申请相应权限 |
| AUTHZ_ROLE_REQUIRED | 403 | 需要特定角色 | 申请相应角色 |
| AUTHZ_DATA_SCOPE_DENIED | 403 | 超出数据范围 | 申请数据范围权限 |
| AUTHZ_RESOURCE_LOCKED | 423 | 资源被锁定 | 等待解锁或联系管理员 |
| AUTHZ_IP_NOT_ALLOWED | 403 | IP 不在白名单 | 联系管理员添加 IP |

## 4. 资源错误 (RES_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| RES_NOT_FOUND | 404 | 资源不存在 | 检查资源 ID |
| RES_ALREADY_EXISTS | 409 | 资源已存在 | 使用其他名称 |
| RES_DELETED | 410 | 资源已删除 | 检查资源状态 |
| RES_TENANT_MISMATCH | 403 | 租户不匹配 | 检查资源归属 |

## 5. 验证错误 (VAL_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| VAL_REQUIRED_FIELD | 422 | 必填字段为空 | 填写必填字段 |
| VAL_INVALID_FORMAT | 422 | 格式错误 | 检查字段格式 |
| VAL_LENGTH_EXCEEDED | 422 | 长度超限 | 缩短内容 |
| VAL_INVALID_EMAIL | 422 | 邮箱格式错误 | 输入有效邮箱 |
| VAL_INVALID_URL | 422 | URL 格式错误 | 输入有效 URL |
| VAL_INVALID_FILE_TYPE | 422 | 文件类型不支持 | 上传支持的文件类型 |
| VAL_FILE_TOO_LARGE | 422 | 文件过大 | 减小文件大小 |
| VAL_INVALID_ENUM | 422 | 枚举值无效 | 使用允许的值 |
| VAL_PAGINATION_INVALID | 422 | 分页参数无效 | 检查分页参数 |

## 6. 状态错误 (STATE_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| STATE_TRANSITION_INVALID | 409 | 状态转换无效 | 检查当前状态 |
| STATE_DOCUMENT_PROCESSING | 409 | 文档处理中 | 等待处理完成 |
| STATE_DOCUMENT_FAILED | 409 | 文档处理失败 | 重新上传或修复 |
| STATE_QA_NOT_PUBLISHED | 409 | 问答未发布 | 先发布问答 |
| STATE_QA_EXPIRED | 410 | 问答已过期 | 重新发布 |
| STATE_INDEX_IN_PROGRESS | 409 | 索引任务进行中 | 等待索引完成 |
| STATE_SESSION_EXPIRED | 401 | 会话已过期 | 重新开始会话 |

## 7. 业务错误 (BIZ_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| BIZ_DOCUMENT_UPLOAD_FAILED | 400 | 文档上传失败 | 检查文件或重试 |
| BIZ_DOCUMENT_PARSE_FAILED | 400 | 文档解析失败 | 检查文档格式 |
| BIZ_CHUNK_EMPTY | 400 | 内容为空 | 检查文档内容 |
| BIZ_QA_NO_REFERENCE | 400 | 缺少引用证据 | 添加参考文档 |
| BIZ_RETRIEVAL_FAILED | 500 | 检索服务异常 | 重试或联系管理员 |
| BIZ_LLM_FAILED | 502 | LLM 服务异常 | 重试或联系管理员 |
| BIZ_EMBEDDING_FAILED | 500 | 向量化失败 | 重试或联系管理员 |
| BIZ_RERANK_FAILED | 500 | 重排序失败 | 重试或跳过重排序 |
| BIZ_FEEDBACK_DUPLICATE | 409 | 重复反馈 | 已反馈过此消息 |
| BIZ_QUOTA_EXCEEDED | 429 | 配额超限 | 等待配额重置 |

## 8. 系统错误 (SYS_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| SYS_DATABASE_ERROR | 500 | 数据库错误 | 联系管理员 |
| SYS_REDIS_ERROR | 500 | 缓存服务错误 | 联系管理员 |
| SYS_STORAGE_ERROR | 500 | 存储服务错误 | 联系管理员 |
| SYS_INTERNAL_ERROR | 500 | 内部错误 | 联系管理员 |
| SYS_MAINTENANCE | 503 | 系统维护中 | 稍后重试 |

## 9. 外部服务错误 (EXT_*)

| 错误码 | HTTP | 说明 | 解决方案 |
|--------|------|------|----------|
| EXT_OPENAI_ERROR | 502 | OpenAI API 错误 | 检查 API 密钥或重试 |
| EXT_ANTHROPIC_ERROR | 502 | Anthropic API 错误 | 检查 API 密钥或重试 |
| EXT_MINIO_ERROR | 502 | MinIO 错误 | 检查存储服务 |
| EXT_OPENSEARCH_ERROR | 502 | OpenSearch 错误 | 检查搜索服务 |

## 10. 错误响应示例

### 10.1 认证失败
```json
{
  "success": false,
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "用户名或密码错误",
    "details": {
      "field": "password"
    }
  },
  "request_id": "req_123456789"
}
```

### 10.2 权限不足
```json
{
  "success": false,
  "error": {
    "code": "AUTHZ_PERMISSION_DENIED",
    "message": "需要权限: document:delete",
    "details": {
      "required_permission": "document:delete"
    }
  },
  "request_id": "req_123456789"
}
```

### 10.3 资源不存在
```json
{
  "success": false,
  "error": {
    "code": "RES_NOT_FOUND",
    "message": "文档不存在: doc_123456",
    "details": {
      "resource_type": "document",
      "resource_id": "doc_123456"
    }
  },
  "request_id": "req_123456789"
}
```

### 10.4 验证失败
```json
{
  "success": false,
  "error": {
    "code": "VAL_REQUIRED_FIELD",
    "message": "数据验证失败",
    "details": {
      "field": "email",
      "reason": "字段不能为空"
    }
  },
  "request_id": "req_123456789"
}
```
