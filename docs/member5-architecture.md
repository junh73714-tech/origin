# 成员5 架构与流程图

---

## 1. 系统总体架构（成员5视角）

```mermaid
graph TB
    subgraph 前端["前端层"]
        M2["成员2: 用户问答前端"]
        M3["成员3: 管理后台前端"]
    end

    subgraph 网关["API网关"]
        API["FastAPI Router"]
    end

    subgraph 核心["成员5核心模块"]
        direction TB
        KB_API["知识库API / 10端点"]
        DOC_API["文档API / 9端点"]
        CHUNK_API["Chunk API"]
        IDX_API["索引任务API / 5端点"]

        KB_SVC["KnowledgeBaseService"]
        DOC_SVC["DocumentService"]
        STORAGE["MinioStorageService"]
        PARSER["ParserDispatcher / 5种格式解析"]
        CHUNKER["DocumentChunker / 8种切分策略"]
        EMBED["EmbeddingProvider / 共享向量化"]
        IDX_SVC["IndexingService / 双索引写入"]
        ORCH["DocumentOrchestrator / 流程编排"]

        KB_API --> KB_SVC
        DOC_API --> DOC_SVC
        DOC_SVC --> STORAGE
        CHUNK_API --> ORCH
        IDX_API --> IDX_SVC
    end

    subgraph 存储["外部存储"]
        PG[("PostgreSQL<br/>+ pgvector")]
        OS[("OpenSearch<br/>BM25")]
        MINIO[("MinIO<br/>文件存储")]
        REDIS[("Redis<br/>缓存/队列")]
    end

    subgraph 下游["下游消费者"]
        M6["成员6: 检索与问答"]
        M7["成员7: 标准问答与评估"]
        M4["成员4: 权限服务"]
        CELERY["Celery Worker"]
    end

    M2 --> API
    M3 --> API
    API --> KB_API
    API --> DOC_API
    API --> CHUNK_API
    API --> IDX_API

    KB_SVC --> PG
    DOC_SVC --> PG
    DOC_SVC --> MINIO
    STORAGE --> MINIO
    PARSER --> STORAGE
    CHUNKER --> PARSER
    EMBED --> PG
    IDX_SVC --> OS
    IDX_SVC --> PG
    IDX_SVC --> EMBED
    ORCH --> PARSER
    ORCH --> CHUNKER
    ORCH --> IDX_SVC

    CELERY --> ORCH
    M6 --> OS
    M6 --> PG
    M6 --> EMBED
    M7 --> ORCH
    M4 --> KB_SVC
    M4 --> DOC_SVC
```

---

## 2. 文档处理完整流水线

```mermaid
flowchart TD
    UPLOAD(["用户上传文档"])
    --> VALIDATE{"文件校验"}
    -->|"扩展名/大小/MIME"| HASH["计算SHA-256"]
    --> DUPCHECK{"重复检查"}
    -->|"新文件"| MINIO_SAVE["存入MinIO"]
    --> DOC_CREATE["创建Document记录"]
    --> VER_CREATE["创建DocumentVersion v1"]
    --> STATUS_PROC["状态: processing"]

    --> PARSE["解析阶段<br/>PDF/DOCX/TXT/MD/HTML"]
    --> PARSE_LOG["记录解析日志"]

    --> CLEAN["清洗阶段<br/>去页眉页脚/合并断裂行<br/>规范化空白"]
    --> CLEAN_LOG["记录清洗日志"]

    --> SPLIT["切分阶段<br/>标题/章节/段落/条款<br/>Token限制/重叠窗口"]
    --> SPLIT_LOG["记录切分日志"]

    --> CHUNK_SAVE["创建DocumentChunk记录<br/>每个Chunk含13个必填字段"]

    --> EMBED_STAGE["Embedding阶段<br/>批量向量化"]
    --> IDX_OS["写入OpenSearch<br/>BM25关键词索引"]
    --> IDX_PG["写入pgvector<br/>向量索引"]

    --> STATUS_REVIEW["状态: pending_review"]
    --> OUTBOX_IDX["Outbox: index.completed"]

    --> MANUAL_CHECK{{"人工检查Chunk质量"}}
    --> PUBLISH_ACTION(["管理员发布"])

    --> STATUS_PUB["状态: published"]
    --> OUTBOX_PUB["Outbox: version.published"]

    OUTBOX_PUB -.-> M6_CACHE["成员6: 缓存失效"]
    OUTBOX_PUB -.-> M7_QA["成员7: 问答待复核"]
    OUTBOX_IDX -.-> M6_READY["成员6: 索引就绪"]
```

---

## 3. 文档状态机

```mermaid
stateDiagram-v2
    [*] --> draft: 上传文档
    draft --> processing: 开始处理
    processing --> failed: 处理异常
    processing --> pending_review: 处理完成
    failed --> draft: 重试

    pending_review --> pending_publish: 人工确认
    pending_review --> draft: 退回修改

    pending_publish --> published: 管理员发布
    pending_publish --> draft: 退回修改

    published --> paused: 暂停检索
    published --> expired: 超过有效期
    published --> offline: 管理员下线
    published --> archived: 归档保存

    paused --> published: 恢复检索
    paused --> offline: 管理员下线

    expired --> offline: 管理员清理
    expired --> archived: 归档保存

    offline --> [*]
    archived --> [*]

    note right of published
        唯一可被成员6检索的状态
        必须同时满足:
        1. 状态 = published
        2. 版本 = current
        3. 未过期
        4. 权限有效
    end note
```

---

## 4. 版本更新流程

```mermaid
flowchart TD
    UPLOAD_V2(["上传新版本文件"])
    --> CREATE_VER["创建新版本记录<br/>旧版本保持可用"]
    --> PARSE_V2["解析+清洗+切分新版本"]
    --> COMPARE{"对比新旧Chunk<br/>基于content_hash"}

    COMPARE -->|"无变化"| SKIP["跳过索引"]
    COMPARE -->|"有变化"| DIFF["生成差异报告<br/>added/deleted/unchanged"]

    DIFF --> INCR_IDX["增量索引<br/>仅索引新增/变更Chunk"]
    INCR_IDX --> VERIFY_IDX["验证新索引可用性"]

    VERIFY_IDX -->|"不可用"| ROLLBACK["回滚: 保留旧版本"]
    VERIFY_IDX -->|"可用"| WAIT_PUB(["等待管理员发布"])

    WAIT_PUB --> PUBLISH_V2["发布新版本"]
    PUBLISH_V2 --> OLD_OFFLINE["旧版本退出正式检索"]
    PUBLISH_V2 --> OUTBOX_PUB["Outbox: version.published"]

    OUTBOX_PUB --> M6_CACHE["成员6: 缓存失效"]
    OUTBOX_PUB --> M7_QA["成员7: 问答待复核"]
    OUTBOX_PUB --> AUDIT["记录审计日志"]
```

---

## 5. 数据模型 ER 图

```mermaid
erDiagram
    KnowledgeBase ||--o{ KnowledgeBasePermission : has
    KnowledgeBase ||--o{ Document : contains
    Document ||--o{ DocumentPermission : has
    Document ||--o{ DocumentVersion : versions
    Document ||--o{ DocumentChunk : chunks
    Document ||--o{ DocumentProcessLog : logs
    DocumentVersion ||--o{ DocumentChunk : chunks
    DocumentChunk ||--o{ IndexTask : triggers

    KnowledgeBase {
        string id PK
        string tenant_id
        string name
        string status
        string business_domain
        int document_count
        int chunk_count
        json settings
    }

    KnowledgeBasePermission {
        string id PK
        string knowledge_base_id FK
        string principal_type
        string principal_id
        string permission_type
        bool is_deny
        datetime effective_time
        datetime expiration_time
    }

    Document {
        string id PK
        string knowledge_base_id FK
        string name
        string original_filename
        string file_type
        string mime_type
        int file_size
        string file_hash
        string file_path
        string status
        int current_version
        int chunk_count
        datetime published_at
        text processing_error
    }

    DocumentVersion {
        string id PK
        string document_id FK
        int version
        string file_hash
        int previous_version
        bool is_current_version
        string publish_status
        datetime effective_time
        datetime expiration_time
    }

    DocumentChunk {
        string id PK
        string knowledge_base_id
        string document_id FK
        string document_version_id FK
        int chunk_no
        string title_path
        int page_start
        int page_end
        int source_offset
        text raw_text
        text clean_text
        string content_hash
        int token_count
        json permission_metadata
        string status
        string index_status
    }

    IndexTask {
        string id PK
        string document_id FK
        string document_version_id
        string chunk_id
        string task_type
        string target
        string idempotent_key UK
        string status
        int retry_count
        text error_message
    }

    DocumentProcessLog {
        string id PK
        string document_id FK
        string document_version_id
        string stage
        string status
        int progress
        text error_message
    }
```

---

## 6. API 端点全景图

```mermaid
graph LR
    subgraph 知识库["知识库 (10端点)"]
        KB_C["POST /knowledge-bases<br/>创建"]
        KB_L["GET /knowledge-bases<br/>列表"]
        KB_G["GET /knowledge-bases/:id<br/>详情"]
        KB_U["PUT /knowledge-bases/:id<br/>编辑"]
        KB_E["PATCH /knowledge-bases/:id/enable<br/>启用"]
        KB_D["PATCH /knowledge-bases/:id/disable<br/>停用"]
        KB_S["GET /knowledge-bases/:id/stats<br/>统计"]
        KB_PC["POST /knowledge-bases/:id/permissions<br/>配置权限"]
        KB_PL["GET /knowledge-bases/:id/permissions<br/>查询权限"]
        KB_PD["DELETE /knowledge-bases/:id/permissions/:pid<br/>删除权限"]
    end

    subgraph 文档["文档 (9端点)"]
        DOC_U["POST /documents/upload<br/>单文件上传"]
        DOC_BU["POST /documents/batch-upload<br/>批量上传"]
        DOC_L["GET /documents<br/>文档列表"]
        DOC_G["GET /documents/:id<br/>文档详情"]
        DOC_P["PATCH /documents/:id/publish<br/>发布"]
        DOC_PS["PATCH /documents/:id/pause<br/>暂停"]
        DOC_O["PATCH /documents/:id/offline<br/>下线"]
        DOC_VL["GET /documents/:id/versions<br/>版本列表"]
        DOC_VD["GET /documents/:id/versions/:vid<br/>版本详情"]
    end

    subgraph Chunk["Chunk (2端点)"]
        CH_L["GET /document-chunks<br/>Chunk列表"]
        CH_G["GET /document-chunks/:id<br/>Chunk详情"]
    end

    subgraph 索引["索引任务 (5端点)"]
        IT_L["GET /index-tasks<br/>任务列表"]
        IT_G["GET /index-tasks/:id<br/>任务详情"]
        IT_R["POST /index-tasks/:id/retry<br/>重试"]
        IT_RB["POST /index-tasks/rebuild<br/>重建索引"]
        IT_CC["POST /index-tasks/consistency-check<br/>一致性检查"]
    end
```

---

## 7. 服务依赖关系

```mermaid
graph TD
    ORCH["DocumentOrchestrator<br/>编排器"]
    PARSER["ParserDispatcher<br/>解析调度器"]
    CHUNKER["DocumentChunker<br/>切分器"]
    IDX["IndexingService<br/>索引服务"]
    STORAGE["MinioStorageService<br/>存储服务"]
    EMBED["EmbeddingProvider<br/>向量化"]
    OS["OpenSearch"]
    PG["PostgreSQL+pgvector"]
    MINIO["MinIO"]

    ORCH --> PARSER
    ORCH --> CHUNKER
    ORCH --> IDX
    ORCH --> STORAGE
    PARSER --> STORAGE
    IDX --> EMBED
    IDX --> OS
    IDX --> PG

    DOC_SVC["DocumentService<br/>文档服务"]
    KB_SVC["KnowledgeBaseService<br/>知识库服务"]

    DOC_SVC --> STORAGE
    KB_SVC --> PG
    DOC_SVC --> PG
```

---

## 8. 项目文件结构（成员5产出）

```text
backend/app/
├── api/
│   ├── knowledge_bases.py    知识库CRUD+启停+统计+权限 (10端点)
│   ├── documents.py           文档上传+管理+发布+版本 (9端点)
│   ├── chunks.py              Chunk查询 (2端点)
│   ├── index_tasks.py         索引任务管理 (5端点)
│   └── ...
├── models/
│   └── document.py            数据模型 (8模型)
│       KnowledgeBase / KnowledgeBasePermission
│       Document / DocumentPermission
│       DocumentVersion / DocumentChunk
│       IndexTask / DocumentProcessLog
├── schemas/
│   └── document.py            请求响应Schema (25+个)
├── services/
│   ├── knowledge_base.py      知识库业务服务
│   ├── document.py            文档业务服务
│   ├── storage.py             MinIO存储服务
│   ├── chunking.py            文档切分服务 (8种策略)
│   ├── indexing.py            索引写入服务 (OS+pgvector)
│   ├── orchestrator.py        文档处理编排器
│   └── parsing/
│       ├── base.py            解析器基类+结果类型
│       ├── pdf_parser.py      PDF解析+OCR接口
│       ├── docx_parser.py     DOCX解析
│       ├── txt_parser.py      TXT解析
│       ├── md_parser.py       Markdown解析
│       ├── html_parser.py     HTML解析
│       └── dispatcher.py      调度器+清洗规则
├── providers/
│   └── embedding.py           共享EmbeddingProvider
├── tasks/
│   └── document.py            Celery异步任务 (4个)
└── core/
    └── celery_app.py          Celery应用工厂

backend/tests/unit/
├── test_document_models.py            模型测试 (52个)
├── test_knowledge_base_service.py     知识库服务测试 (15个)
├── test_document_service.py           文档服务测试 (20个)
├── test_storage.py                    存储服务测试 (39个)
├── test_parsing.py                    解析服务测试 (35个)
├── test_chunking.py                   切分服务测试 (19个)
├── test_embedding.py                  Embedding测试 (10个)
├── test_indexing.py                   索引服务测试 (8个)
└── test_orchestrator.py              编排器测试 (12个)
```
