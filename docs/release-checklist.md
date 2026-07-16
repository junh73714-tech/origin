# 发布检查清单

## 1. 发布前检查

### 1.1 代码检查
- [ ] 所有功能分支已合并到 `develop`
- [ ] `develop` 分支构建成功
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 代码覆盖率不低于上一版本

### 1.2 安全检查
- [ ] 依赖漏洞扫描通过
- [ ] 无硬编码密钥或凭据
- [ ] 权限边界已验证
- [ ] SQL 注入防护已确认
- [ ] XSS 防护已确认

### 1.3 性能检查
- [ ] API 响应时间符合预期
- [ ] 数据库查询性能达标
- [ ] 内存使用正常
- [ ] 无内存泄漏

### 1.4 文档检查
- [ ] API 文档与代码一致
- [ ] 数据库文档已更新
- [ ] README 已更新
- [ ] 部署文档已更新
- [ ] 变更日志已记录

## 2. 发布执行

### 2.1 预发布
```bash
# 1. 创建发布分支
git checkout develop
git pull
git checkout -b release/v0.x.y

# 2. 更新版本号
# backend/app/core/config.py
# frontend/package.json

# 3. 提交发布分支
git add .
git commit -m "chore(release): v0.x.y"

# 4. 创建标签
git tag v0.x.y
```

### 2.2 合并到 main
```bash
# 1. 合并到 main
git checkout main
git merge release/v0.x.y --no-ff

# 2. 推送
git push origin main
git push origin v0.x.y

# 3. 合并回 develop
git checkout develop
git merge release/v0.x.y --no-ff
git push origin develop

# 4. 删除发布分支
git branch -d release/v0.x.y
```

### 2.3 Docker 镜像构建
```bash
# 构建镜像
docker build -t rag-knowledge-backend:v0.x.y ./backend
docker build -t rag-knowledge-frontend:v0.x.y ./frontend

# 推送镜像
docker push rag-knowledge-backend:v0.x.y
docker push rag-knowledge-frontend:v0.x.y
```

## 3. 部署验证

### 3.1 健康检查
```bash
# API 健康检查
curl http://localhost:8000/api/v1/health

# 前端健康检查
curl http://localhost:3000

# 数据库连接
psql -h localhost -U rag_user -d rag_knowledge -c "SELECT 1"

# Redis 连接
redis-cli ping
```

### 3.2 功能验证
- [ ] 用户可以登录
- [ ] 可以创建知识库
- [ ] 可以上传文档
- [ ] 可以发起问答
- [ ] 可以查看历史记录
- [ ] 管理后台可访问

### 3.3 冒烟测试
```bash
# 运行冒烟测试
make smoke-test
```

## 4. 发布后检查

### 4.1 监控检查
- [ ] Prometheus 指标正常
- [ ] Grafana 看板正常
- [ ] 日志正常输出
- [ ] 无异常告警

### 4.2 用户反馈
- [ ] 核心用户已验证
- [ ] 无严重问题反馈
- [ ] 性能表现正常

## 5. 回滚准备

### 5.1 回滚触发条件
- 严重功能缺陷
- 数据损坏
- 安全漏洞
- 性能严重下降

### 5.2 回滚步骤
```bash
# 1. 停止服务
docker-compose down

# 2. 切换到上一版本
git checkout v0.x.(y-1)

# 3. 重新构建
docker build -t rag-knowledge-backend:v0.x.(y-1) ./backend
docker build -t rag-knowledge-frontend:v0.x.(y-1) ./frontend

# 4. 回滚数据库（如需要）
alembic downgrade -1

# 5. 启动服务
docker-compose up -d
```

## 6. 版本号规范

使用语义化版本 (SemVer):
- 主版本 (MAJOR): 不兼容的 API 变更
- 次版本 (MINOR): 向后兼容的功能新增
- 修订版 (PATCH): 向后兼容的问题修复

格式: `v{MAJOR}.{MINOR}.{PATCH}`

示例: `v0.1.0`, `v1.0.0`
