<<<<<<< HEAD
<<<<<<< HEAD
# origin

=======
=======
>>>>>>> 8de89ee904f686dbe7d52e3b35cdc79ef917eeb2
# 企业级混合检索 RAG 知识问答平台

企业级混合检索 RAG 知识问答平台，支持 Keyword Retrieval、Vector Retrieval、RRF 融合与 Reranker。

## 技术栈

### 后端
- Python 3.10+
- FastAPI
- SQLAlchemy 2.x (Async)
- Alembic
- PostgreSQL + pgvector
- OpenSearch
- Redis
- Celery
- MinIO

### 前端
- React 18
- TypeScript 5
- Vite 5
- Ant Design 5
- Zustand

### 基础设施
- Docker Compose
- Nginx
- Prometheus
- Grafana

## 项目结构

```
rag-knowledge/
├── backend/              # 后端应用
│   ├── app/
│   │   ├── api/        # API 路由
│   │   ├── core/       # 核心配置
│   │   ├── db/         # 数据库连接
│   │   ├── models/     # 数据模型
│   │   ├── schemas/    # Pydantic Schema
│   │   ├── services/   # 业务服务
│   │   ├── tasks/      # Celery 任务
│   │   └── utils/      # 工具函数
│   ├── tests/          # 测试
│   └── alembic/        # 数据库迁移
├── frontend/           # 前端应用
│   └── src/
│       ├── api/       # API 调用
│       ├── components/ # 组件
│       ├── pages/     # 页面
│       ├── routes/    # 路由
│       └── store/     # 状态管理
├── deploy/             # 部署配置
│   ├── docker/        # Docker 配置
│   └── nginx/         # Nginx 配置
├── docs/               # 文档
├── scripts/            # 脚本
└── sample_data/        # 示例数据
```

## 快速开始

### 前置要求

- Docker 和 Docker Compose
- Python 3.10+
- Node.js 18+

### 1. 克隆仓库

```bash
git clone <repository-url>
cd rag-knowledge
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际配置
```

### 3. 启动开发环境

```bash
make dev-up
```

### 4. 数据库迁移

```bash
make migrate
make seed  # 可选：初始化示例数据
```

### 5. 访问应用

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- Grafana：http://localhost:3100

## 开发命令

```bash
# 后端
make backend-test     # 后端测试
make lint            # 代码检查
make format          # 代码格式化

# 前端
make frontend-test   # 前端测试

# 全量
make test           # 所有测试
make dev-up         # 启动开发环境
make dev-down       # 停止开发环境
make logs           # 查看日志
make reset-dev      # 重置开发环境
```

## 团队成员

- 成员1：技术负责人、架构与集成发布
- 成员2：前端用户端页面
- 成员3：前端管理端页面
- 成员4：用户认证与权限管理
- 成员5：文档解析与 Chunk 管理
- 成员6：检索与问答生成
- 成员7：标准问答与评估

## 分支规范

- `main`：生产分支
- `develop`：集成分支
- `chore/m1-*`：成员1公共工程
- `feature/m{2-7}-*`：各成员功能分支

## 许可证

MIT
<<<<<<< HEAD
>>>>>>> 8de89ee904f686dbe7d52e3b35cdc79ef917eeb2
=======
>>>>>>> 8de89ee904f686dbe7d52e3b35cdc79ef917eeb2
