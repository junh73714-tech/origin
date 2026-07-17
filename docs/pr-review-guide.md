# PR 评审指南

> 本文档定义 PR 评审的流程、标准和要求，确保代码质量和团队协作效率。

---

## 1. PR 信息

| 项目 | 内容 |
|------|------|
| **PR 标题** | fix(m1): 完善基础设施配置，修复验收测试问题 |
| **分支** | `feature/m1-infrastructure-fix` → `develop` |
| **发起人** | 成员1（组长） |
| **创建时间** | 2026-07-17 |

---

## 2. 需要评审的成员

### 评审人分配

| 成员 | 评审内容 | 评审理由 |
|------|---------|---------|
| **成员2/3（前端）** | `frontend/` 相关变更（如有） | 确保前端构建不受影响 |
| **成员5（文档处理）** | `backend/pyproject.toml` | 依赖变更可能影响文档解析模块 |
| **成员7（部署）** | `deploy/docker/docker-compose.yml` | Docker 配置变更 |
| **组长（成员1）** | `backend/app/core/config.py` | 核心配置模块，自审 |

### 评审角色说明

- **required（必须）**: 必须审核通过才能合并
- **optional（可选）**: 建议审核，但非强制

---

## 3. 评审内容清单

### 3.1 基础设施评审（成员1自审）

- [ ] `backend/app/core/config.py`
  - [ ] AppSettings 结构是否合理
  - [ ] 配置同步逻辑是否正确
  - [ ] `extra="ignore"` 是否影响现有功能

- [ ] `backend/app/core/security.py`
  - [ ] bcrypt 直接调用是否安全
  - [ ] 通配符权限逻辑是否正确
  - [ ] 密码哈希长度限制是否合理

- [ ] `.gitignore`
  - [ ] lock 文件忽略规则是否完整

### 3.2 依赖评审（成员5）

- [ ] `backend/pyproject.toml`
  - [ ] 新增依赖是否与现有代码兼容
  - [ ] `hatch.build` 配置是否正确
  - [ ] `ruff.lint` 配置是否符合项目规范
  - [ ] `mypy` 宽松模式是否可接受

### 3.3 部署评审（成员7）

- [ ] `deploy/docker/docker-compose.yml`
  - [ ] backend 服务定义是否正确
  - [ ] frontend 服务定义是否正确
  - [ ] 环境变量映射是否完整
  - [ ] healthcheck 配置是否合理
  - [ ] 服务依赖顺序是否正确

---

## 4. 评审要求

### 4.1 代码质量标准

| 检查项 | 标准 | 说明 |
|--------|------|------|
| **语法正确** | 通过 ruff check | 无语法错误 |
| **类型安全** | mypy 通过 | 允许部分类型注解缺失 |
| **测试覆盖** | 276+ 测试通过 | 原有测试不受影响 |
| **功能完整** | `docker compose config` 通过 | 配置有效 |

### 4.2 安全性标准

| 检查项 | 标准 |
|--------|------|
| **密码安全** | bcrypt 正确实现 |
| **权限控制** | 通配符逻辑正确 |
| **敏感信息** | 无硬编码密钥 |

### 4.3 兼容性标准

| 检查项 | 标准 |
|--------|------|
| **向后兼容** | 不破坏现有功能 |
| **环境变量** | 使用标准前缀 |
| **Docker** | 可正常构建镜像 |

---

## 5. 评审通过标准

### 5.1 必须满足的条件（全部通过才能合并）

- [ ] **至少 2 位成员审核通过**（含成员1自审）
- [ ] **所有 CI 检查通过**
  - [ ] `docker compose config --quiet` 通过
  - [ ] `make backend-test` 276+ passed
  - [ ] `make frontend-test` 7+ passed
- [ ] **无严重问题（Critical/Blocker）**
- [ ] **无未解决的冲突**

### 5.2 问题严重程度定义

| 等级 | 定义 | 处理方式 |
|------|------|---------|
| **Critical** | 功能完全不可用、安全漏洞 | 必须修复 |
| **Major** | 功能部分受损 | 应该修复 |
| **Minor** | 代码风格、格式问题 | 建议修复 |
| **Info** | 优化建议 | 可忽略 |

### 5.3 评审结论选项

| 结论 | 条件 |
|------|------|
| **Approved** | 所有检查通过，可合并 |
| **Request Changes** | 有 Critical/Major 问题需修复 |
| **Comment** | 只有 Minor/Info 问题，可选修复 |

---

## 6. 评审流程

### 6.1 评审步骤

```
1. PR 创建 → 自动通知评审人
2. 评审人下载分支 → 本地验证
3. 评审人给出结论 → Approved / Request Changes / Comment
4. 发起人处理反馈 → 如有问题则修改
5. 评审通过 → 组长合并 PR
```

### 6.2 本地验证命令

```bash
# 1. 拉取 PR 分支
git fetch origin feature/m1-infrastructure-fix
git checkout feature/m1-infrastructure-fix

# 2. 验证 docker 配置
docker compose -f deploy/docker/docker-compose.yml config --quiet

# 3. 运行后端测试
cd backend && pytest tests/ -v --ignore=tests/integration

# 4. 运行前端测试
cd frontend && npm run test -- --run

# 5. 代码检查
cd backend && ruff check app/ tests/
cd backend && mypy app/ --ignore-missing-imports
```

---

## 7. 评审记录模板

### 评审人填写

```markdown
## 评审记录

### 评审人：[成员名称]
### 评审时间：[日期]

#### 代码审查
- [ ] 功能完整性：✅ / ❌
- [ ] 代码质量：✅ / ❌
- [ ] 安全性：✅ / ❌
- [ ] 兼容性：✅ / ❌

#### 问题列表
| 等级 | 问题描述 | 文件:行号 | 状态 |
|------|---------|-----------|------|
| - | - | - | - |

#### 结论
- [ ] Approved
- [ ] Request Changes
- [ ] Comment

#### 备注
（可选）
```

---

## 8. 常见问题

### Q1: 评审超时怎么办？
**A**: 设置 48 小时响应期限，超时后默认 Approved（无严重问题时）。

### Q2: 评审意见冲突怎么办？
**A**: 由组长（成员1）做最终决定。

### Q3: 发现新问题怎么办？
**A**: 在当前 PR 中继续讨论，不开新 PR。

### Q4: 紧急修复可以跳过评审吗？
**A**: 不可以。所有修改必须经过评审，紧急情况由组长决定。

---

## 9. 附录

### 9.1 相关文档

- [项目 CLAUDE.md](./CLAUDE.md) - 项目规范
- [API 契约文档](./docs/api-contracts.md) - 接口规范
- [错误码文档](./docs/error-codes.md) - 错误码定义

### 9.2 联系方式

| 成员 | 职责 | 备注 |
|------|------|------|
| 成员1 | 组长、基础设施 | 本 PR 发起人 |
| 成员2/3 | 前端 | - |
| 成员4 | 认证权限 | - |
| 成员5 | 文档处理 | - |
| 成员6 | 检索排序 | - |
| 成员7 | 问答系统 | - |

---

*本文档由 Claude Code 自动生成*
*创建时间: 2026-07-17*
