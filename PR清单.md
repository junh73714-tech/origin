# PR 清单

> 生成时间：2026-07-17
> Gitea 仓库：http://localhost:3010/admin/origin
> GitHub 仓库：https://github.com/junh73714-tech/origin

---

## 一、已合并的 PR

| PR | 分支 | 成员 | 说明 | 合并时间 |
|----|------|------|------|----------|
| PR #8 | feature/m5-document-pipeline | M5 | 文档管道初版 | 已合并 |
| PR #9 | feature/m5-document-pipeline | M5 | Chunk API 补充 | 已合并 |
| PR #11 | feature/member4-identity-auth | M4 | 身份认证与权限系统 | 已合并 |
| PR #13 | feature/m1-infrastructure-fix | M1 | 基础设施配置修复 | 已合并 |

### 已合并的 M3 相关分支

| 分支 | 说明 | 状态 |
|------|------|------|
| feature/m3-admin-pages-1 | M2 用户权限与文档页面 | ⚠️ 有问题待处理 |
| feature/m3-admin-pages-2 | M3 问答优化与检索调试 | ⚠️ 有问题待处理 |
| feature/m3-admin-pages-3 | M4 评估、安全、设置页面 | ⚠️ 有问题待处理 |
| feature/m3-admin-skeleton | M1 管理后台骨架 | ⚠️ 有问题待处理 |

---

## 二、待合并的 PR

### 1. feature/m2-user-chat（成员2 - 前端用户端页面）

| 项目 | 内容 |
|------|------|
| 最新提交 | 780b412 feat(m2-auth): 对齐成员4新增的认证契约（密码重置/锁定/数据范围） |
| 提交时间 | 2026-07-17 |
| 依赖 | M4（已完成） |
| 状态 | 待提交 PR |

**待做**：
- [ ] 同步 develop 最新代码
- [ ] 本地测试
- [ ] 提交 PR

---

### 2. feature/m6-hybrid-retrieval（成员6 - 检索与问答）

| 项目 | 内容 |
|------|------|
| 最新提交 | d7e2b5e test(m6): add /qa/chat SSE end-to-end self-test |
| 提交时间 | 2026-07-17 |
| 依赖 | M4, M5（已完成） |
| 状态 | 待提交 PR |

**待做**：
- [ ] 同步 develop 最新代码
- [ ] 解决迁移文件 004_m6_retrieval_logs.py
- [ ] 本地测试
- [ ] 提交 PR

---

### 3. feature/m7（成员7 - 标准问答与评估）

| 项目 | 内容 |
|------|------|
| 最新提交 | c15ed48 feat(m7): 完成标准问答、评估、监控模块的代码修复和测试补充 |
| 提交时间 | 2026-07-17 |
| 依赖 | M4, M5, M6 |
| 状态 | 待提交 PR |

**待做**：
- [ ] 同步 develop 最新代码
- [ ] 本地测试
- [ ] 提交 PR

---

### 4. m3-admin-console（成员3 - 前端管理端页面）

| 项目 | 内容 |
|------|------|
| 最新提交 | e04fe58 fix(m3): 修复 LoadingState Spin tip 不渲染问题 — 嵌套模式 |
| 提交时间 | 2026-07-17 |
| 说明 | 新版管理端页面，替换旧版 M3 分支 |
| 状态 | 待提交 PR |

**待做**：
- [ ] 同步 develop 最新代码
- [ ] 本地测试
- [ ] 提交 PR

---

### 5. feature/m3-integration-guide（成员3 - 联调指南）

| 项目 | 内容 |
|------|------|
| 最新提交 | eb06e8e docs(m3): 添加管理后台前端联调操作说明 |
| 提交时间 | 2026-07-17 |
| 说明 | 文档分支 |
| 状态 | 待提交 PR |

---

## 三、待处理的问题

### 问题1：M3 旧版本需要处理

| 项目 | 内容 |
|------|------|
| 问题 | feature/m3-admin-pages-* 已合并到 develop，但有问题 |
| 影响 | 需要 revert 旧版代码 |
| 解决方案 | m3-admin-console 是新版，待合并替换 |

### 问题2：M6 迁移文件 004

| 项目 | 内容 |
|------|------|
| 问题 | M6 分支有 004_m6_retrieval_logs.py，但 develop 没有 |
| 影响 | 迁移链不完整 |
| 解决方案 | 需要合并前同步迁移文件 |

---

## 四、成员操作指南

### 各成员下一步

| 成员 | 当前状态 | 下一步操作 |
|------|----------|------------|
| 成员1 | ✅ 已合并 M5, M4 | 协调推进剩余 PR 合并 |
| 成员2 | 待提交 PR | git pull develop → 开发 → 提交 PR |
| 成员3 | 待提交 PR | git pull develop → 测试 → 提交 PR |
| 成员4 | ✅ 已完成 | 协助评审其他成员代码 |
| 成员5 | ✅ 已完成 | 灌数据给成员6联调 |
| 成员6 | 待提交 PR | git pull develop → 测试 → 提交 PR |
| 成员7 | 待提交 PR | git pull develop → 测试 → 提交 PR |

### Git 操作命令

```bash
# 1. 同步最新代码
git checkout develop
git pull origin develop

# 2. 切换到功能分支
git checkout feature/m2-user-chat

# 3. 合并 develop 解决冲突
git merge develop

# 4. 推送代码
git push origin feature/m2-user-chat

# 5. 在 Gitea 上创建 PR
# 访问：http://localhost:3010/admin/origin/pulls/new
```

---

## 五、数据库迁移状态

| 迁移 | 内容 | 状态 |
|------|------|------|
| 001 | 基础表结构 | ✅ 完成 |
| 002 | M5 字段补充 | ✅ 完成 |
| 003 | M4 权限表 | ✅ 完成 |

**共享数据库操作**：
```bash
# 重置数据库
DELETE FROM alembic_version;
# 或
DROP TABLE IF EXISTS alembic_version CASCADE;
# 然后
alembic downgrade base
alembic upgrade head
```

---

## 六、GitHub 仓库

所有代码已同步到 GitHub：
```
https://github.com/junh73714-tech/origin
```

各成员可以将 remote 切换到 GitHub：
```bash
git remote set-url origin https://github.com/junh73714-tech/origin.git
```
