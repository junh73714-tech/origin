# 数据模型文档

## 1. 概述

所有表都包含以下公共字段：
- `id`: 主键 (UUID)
- `tenant_id`: 租户 ID
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `created_by`: 创建人 ID
- `updated_by`: 更新人 ID

## 2. 实体关系图

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   Tenant     │       │    User      │       │    Role      │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │       │ id (PK)      │
│ name         │       │ tenant_id(FK)│───────│ code         │
│ status       │       │ email        │       │ name         │
│ settings     │       │ username     │       │ description  │
└──────────────┘       │ password_hash│       │ is_system    │
       │                └──────┬───────┘       └──────┬───────┘
       │                       │                       │
       │                       │                       │
       │                ┌──────┴───────┐       ┌──────┴───────┐
       │                │  user_roles  │       │role_permissions│
       │                │(association) │       │(association) │
       │                └──────────────┘       └──────────────┘
       │                                               │
       │                                               │
       ▼                                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                          KnowledgeBase                             │
├──────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ tenant_id(FK)                                                    │
│ name, description, icon, is_public, settings                      │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                           Document                                │
├──────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ tenant_id(FK)                                                    │
│ knowledge_base_id(FK)                                            │
│ name, file_type, file_size, file_path, status                    │
│ char_count, metadata, current_version                             │
└──────┬─────────────────────────────────┬────────────────────────┘
       │                                 │
       │                                 │
       ▼                                 ▼
┌──────────────┐                 ┌──────────────────┐
│DocumentVersion│               │ DocumentChunk     │
├──────────────┤               ├──────────────────┤
│ id (PK)      │               │ id (PK)          │
│ document_id  │               │ document_id(FK)  │
│ version      │               │ version          │
│ file_path    │               │ content          │
│ change_summary               │ content_hash     │
│ is_active    │               │ chunk_index      │
└──────────────┘               │ char_start/end   │
                               │ index_status     │
                               └────────┬─────────┘
                                        │
                                        │ references
                                        ▼
                               ┌──────────────────┐
                               │   StandardQA     │
                               ├──────────────────┤
                               │ id (PK)          │
                               │ knowledge_base_id│
                               │ question, answer  │
                               │ keywords, category│
                               │ status, priority  │
                               │ view_count       │
                               │ use_count        │
                               └────────┬─────────┘
                                        │
                                        │
                                        ▼
                               ┌──────────────────┐
                               │  Conversation    │
                               ├──────────────────┤
                               │ id (PK)          │
                               │ user_id(FK)      │
                               │ session_id       │
                               │ title, status    │
                               └────────┬─────────┘
                                        │
                                        │
                                        ▼
                               ┌──────────────────┐
                               │    Message       │
                               ├──────────────────┤
                               │ id (PK)          │
                               │ conversation_id  │
                               │ role, content    │
                               │ intent           │
                               │ matched_qa_id    │
                               │ confidence       │
                               │ references       │
                               │ feedback         │
                               └──────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                         AuditLog                                  │
├──────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ tenant_id(FK), user_id(FK)                                       │
│ action, resource_type, resource_id                               │
│ request_id, ip_address, user_agent                               │
│ method, path, status_code, duration_ms                           │
│ request_body, response_body, details                              │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       SecurityEvent                              │
├──────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ event_type, severity, user_id, tenant_id                         │
│ ip_address, description, details                                 │
│ resolved, resolved_at, resolved_by                               │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       OutboxEvent                                 │
├──────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ event_type, aggregate_type, aggregate_id                         │
│ payload (JSONB)                                                  │
│ published, published_at, retry_count                             │
│ error_message                                                    │
└──────────────────────────────────────────────────────────────────┘
```

## 3. 表结构详解

### 3.1 Tenant (租户表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 租户 ID |
| name | VARCHAR(255) | 租户名称 |
| status | VARCHAR(50) | 状态: active, suspended, deleted |
| settings | JSONB | 租户配置 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 3.2 User (用户表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 用户 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| email | VARCHAR(255) UNIQUE | 邮箱 |
| username | VARCHAR(100) UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | 密码哈希 |
| full_name | VARCHAR(100) | 姓名 |
| phone | VARCHAR(20) | 手机号 |
| is_active | BOOLEAN | 是否激活 |
| is_superuser | BOOLEAN | 是否超级管理员 |

### 3.3 Permission (权限表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 权限 ID |
| tenant_id | VARCHAR(64) | 租户 ID |
| name | VARCHAR(100) | 权限名称 |
| code | VARCHAR(100) UNIQUE | 权限编码 |
| resource_type | VARCHAR(50) | 资源类型 |
| action | VARCHAR(50) | 操作类型 |

### 3.4 Role (角色表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 角色 ID |
| tenant_id | VARCHAR(64) | 租户 ID |
| name | VARCHAR(100) | 角色名称 |
| code | VARCHAR(100) UNIQUE | 角色编码 |
| description | TEXT | 描述 |
| is_system | BOOLEAN | 是否系统内置 |

### 3.5 KnowledgeBase (知识库表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 知识库 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| name | VARCHAR(255) | 名称 |
| description | TEXT | 描述 |
| icon | VARCHAR(255) | 图标 URL |
| is_public | BOOLEAN | 是否公开 |
| settings | JSONB | 配置 |

### 3.6 Document (文档表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 文档 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| knowledge_base_id | VARCHAR(64) FK | 知识库 ID |
| name | VARCHAR(255) | 文档名称 |
| file_type | VARCHAR(50) | 文件类型 |
| file_size | INTEGER | 文件大小 |
| file_path | VARCHAR(500) | MinIO 路径 |
| status | VARCHAR(50) | 状态: pending, processing, completed, failed |
| char_count | INTEGER | 字符数 |
| metadata | JSONB | 元数据 |
| current_version | INTEGER | 当前版本 |

### 3.7 DocumentVersion (文档版本表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 版本 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| document_id | VARCHAR(64) FK | 文档 ID |
| version | INTEGER | 版本号 |
| file_path | VARCHAR(500) | MinIO 路径 |
| file_size | INTEGER | 文件大小 |
| change_summary | TEXT | 变更说明 |
| is_active | BOOLEAN | 是否激活版本 |

### 3.8 DocumentChunk (文档片段表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | Chunk ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| document_id | VARCHAR(64) FK | 文档 ID |
| version | INTEGER | 所属版本 |
| content | TEXT | 内容 |
| content_hash | VARCHAR(64) | 内容哈希 |
| chunk_index | INTEGER | 顺序索引 |
| char_start | INTEGER | 原文起始位置 |
| char_end | INTEGER | 原文结束位置 |
| metadata | JSONB | 元数据 |
| index_status | VARCHAR(50) | 索引状态 |

### 3.9 IndexTask (索引任务表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 任务 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| document_id | VARCHAR(64) FK | 文档 ID |
| task_type | VARCHAR(50) | 任务类型: keyword, vector, both |
| status | VARCHAR(50) | 状态 |
| progress | INTEGER | 进度 0-100 |
| total_chunks | INTEGER | 总 Chunk 数 |
| indexed_chunks | INTEGER | 已索引数 |

### 3.10 StandardQA (标准问答表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 问答 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| knowledge_base_id | VARCHAR(64) FK | 知识库 ID |
| question | TEXT | 问题 |
| answer | TEXT | 答案 |
| keywords | JSONB | 关键词 |
| category | VARCHAR(100) | 分类 |
| status | VARCHAR(50) | 状态: draft, published, unpublished |
| priority | INTEGER | 优先级 |
| view_count | INTEGER | 浏览次数 |
| use_count | INTEGER | 使用次数 |

### 3.11 Conversation (会话表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 会话 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| user_id | VARCHAR(64) | 用户 ID |
| session_id | VARCHAR(64) | 会话标识 |
| title | VARCHAR(255) | 标题 |
| status | VARCHAR(50) | 状态: active, archived |

### 3.12 Message (消息表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 消息 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| conversation_id | VARCHAR(64) FK | 会话 ID |
| role | VARCHAR(20) | 角色: user, assistant |
| content | TEXT | 内容 |
| intent | VARCHAR(100) | 意图 |
| matched_qa_id | VARCHAR(64) FK | 匹配的标准问答 |
| confidence | FLOAT | 置信度 |
| references | JSONB | 引用列表 |
| feedback | VARCHAR(50) | 反馈 |

### 3.13 AuditLog (审计日志表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 日志 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| user_id | VARCHAR(64) | 用户 ID |
| action | VARCHAR(100) | 操作 |
| resource_type | VARCHAR(50) | 资源类型 |
| resource_id | VARCHAR(64) | 资源 ID |
| request_id | VARCHAR(100) | 请求 ID |
| ip_address | VARCHAR(45) | IP 地址 |
| method | VARCHAR(10) | HTTP 方法 |
| path | VARCHAR(500) | 请求路径 |
| status_code | INTEGER | 状态码 |
| duration_ms | INTEGER | 耗时(毫秒) |

### 3.14 OutboxEvent (Outbox 事件表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(64) PK | 事件 ID |
| tenant_id | VARCHAR(64) FK | 租户 ID |
| event_type | VARCHAR(100) | 事件类型 |
| aggregate_type | VARCHAR(50) | 聚合类型 |
| aggregate_id | VARCHAR(64) | 聚合 ID |
| payload | JSONB | 事件数据 |
| published | BOOLEAN | 是否已发布 |
| published_at | TIMESTAMP | 发布时间 |
| retry_count | INTEGER | 重试次数 |
| error_message | TEXT | 错误信息 |

## 4. 索引规范

### 4.1 必须索引
- 所有外键字段
- tenant_id (数据隔离)
- status (状态查询)
- created_at (时间排序)

### 4.2 组合索引
- `ix_knowledge_bases_tenant_name`: (tenant_id, name)
- `ix_documents_tenant_status`: (tenant_id, status)
- `ix_documents_tenant_kb`: (tenant_id, knowledge_base_id)
- `ix_standard_qas_status_category`: (status, category)

## 5. 软删除规范

以下表支持软删除：
- User: 使用 `is_active` 字段
- Document: 使用 `status = 'deleted'`
- StandardQA: 使用 `status = 'deleted'`

其他表使用 `deleted_at` 字段软删除。
