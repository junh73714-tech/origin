# Gitea 七人协作提交与项目合并指南

## 1. 概述

本文档描述团队成员如何通过 Gitea 进行代码协作，包括分支管理、提交规范和 Pull Request 流程。

## 2. 仓库信息

- **仓库地址**: 由组长提供
- **默认分支**: `main` (保护分支)
- **集成分支**: `develop` (保护分支)
- **成员分支**: `chore/m1-*`, `feature/m2-*` 等

## 3. 分支命名规范

| 成员 | 分支前缀 | 示例 |
|------|----------|------|
| 成员1 | `chore/m1-` | `chore/m1-shared-foundation` |
| 成员2 | `feature/m2-` | `feature/m2-user-pages` |
| 成员3 | `feature/m3-` | `feature/m3-admin-pages` |
| 成员4 | `feature/m4-` | `feature/m4-auth-permission` |
| 成员5 | `feature/m5-` | `feature/m5-document-chunk` |
| 成员6 | `feature/m6-` | `feature/m6-retrieval-qa` |
| 成员7 | `feature/m7-` | `feature/m7-standard-qa-eval` |

## 4. 提交信息规范

### 4.1 提交格式

```
<类型>(mX): <简明说明>

[可选的详细说明]
```

### 4.2 提交类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `docs` | 文档更新 |
| `chore` | 构建/工具变更 |

### 4.3 示例

```bash
git commit -m "feat(m4): 添加用户登录接口"

git commit -m "fix(m5): 修复文档解析空指针异常

- 添加空值检查
- 添加单元测试"
```

## 5. 开发流程

### 5.1 开始新任务

```bash
# 1. 确保 develop 是最新的
git checkout develop
git pull origin develop

# 2. 创建功能分支
git switch -c feature/m5-document-upload

# 3. 开发...
# 4. 提交
git add .
git commit -m "feat(m5): 添加文档上传功能"
```

### 5.2 同步 develop

```bash
# 1. 切回 develop
git checkout develop

# 2. 拉取最新
git pull origin develop

# 3. 切回功能分支
git switch feature/m5-document-upload

# 4. 合并 develop
git merge develop

# 5. 解决冲突（如有）
# 6. 推送
git push origin feature/m5-document-upload
```

### 5.3 创建 Pull Request

1. 推送分支到 Gitea:
```bash
git push -u origin feature/m5-document-upload
```

2. 在 Gitea Web 界面创建 Pull Request:
   - 目标分支: `develop`
   - 填写标题和描述
   - 关联相关 Issue
   - 指定评审人员

### 5.4 评审和合并

1. **评审阶段**:
   - 评审人员检查代码
   - 提出修改意见
   - 作者根据意见修改

2. **合并条件**:
   - 所有评审通过
   - CI/CD 通过
   - 无冲突

3. **合并操作**:
   - 使用 Squash Merge 保持历史清晰
   - 删除源分支

## 6. 注意事项

### 6.1 禁止事项

- 禁止直接向 `main` 或 `develop` 推送
- 禁止强制推送 (`git push -f`)
- 禁止在集成分支上开发
- 禁止提交敏感信息到仓库

### 6.2 数据库迁移

- 迁移脚本必须可逆
- 不得修改已合并的迁移
- 迁移前同步 develop

### 6.3 API 变更

- 向后兼容优先
- 破坏性变更需评审
- 更新文档

## 7. 冲突处理

### 7.1 预防冲突

- 频繁同步 develop
- 小步提交
- 及时沟通

### 7.2 解决冲突

```bash
# 1. 同步最新 develop
git fetch origin
git merge origin/develop

# 2. 手动解决冲突
# 编辑冲突文件

# 3. 标记冲突解决
git add <resolved-files>
git commit

# 4. 推送
git push
```

## 8. 发布流程

1. 创建发布分支:
```bash
git checkout develop
git switch -c release/v0.1.0
```

2. 更新版本号并提交

3. 合并到 main:
```bash
git checkout main
git merge release/v0.1.0 --no-ff
git tag v0.1.0
git push origin main --tags
```

4. 合并回 develop:
```bash
git checkout develop
git merge release/v0.1.0 --no-ff
git push origin develop
```
