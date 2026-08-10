# 成员3 管理后台前端 联调操作说明

> 版本：v1.0
> 日期：2026-07-17
> 作者：成员3（管理后台前端）
> 源分支：`feature/m3-admin-skeleton` → 目标分支：`develop`

---

## 一、联调概览

成员3 管理后台前端需要与以下成员进行接口联调：

| 对接成员 | 对接模块 | 接口数量 | 状态 |
|----------|----------|----------|------|
| 成员5 | 知识库/文档/Chunk/索引任务 | 11个接口 | 待联调 |
| 成员4 | 身份认证/RBAC/权限/审计 | 30+个接口 | 待联调 |

---

## 二、与成员5 联调：知识库与文档接口

### 2.1 成员5 提供的后台接口

> 来源：成员5 联调操作说明 第六节

| 端点 | 用途 | 对应前端页面 |
|------|------|-------------|
| `GET /api/v1/knowledge-bases` | 知识库列表（分页+搜索+状态筛选） | 知识库管理 |
| `GET /api/v1/knowledge-bases/{id}` | 知识库详情 | 知识库编辑 |
| `GET /api/v1/knowledge-bases/{id}/stats` | 文档/Chunk/索引统计 | 工作台 |
| `GET /api/v1/documents` | 文档列表（分页+状态+类型筛选） | 文档管理 |
| `GET /api/v1/documents/{id}` | 文档详情（含处理进度+失败原因） | 文档详情 |
| `GET /api/v1/documents/{id}/versions` | 版本列表 | 版本管理 |
| `GET /api/v1/document-chunks` | Chunk列表（分页+搜索） | Chunk查看 |
| `GET /api/v1/document-chunks/{id}` | Chunk详情（含原始文本） | Chunk详情 |
| `GET /api/v1/index-tasks` | 索引任务列表（分页+状态筛选） | 任务监控 |
| `POST /api/v1/index-tasks/{id}/retry` | 重试失败任务 | 任务操作 |

### 2.2 成员3 需要确认的事项

1. **接口响应字段完整性**
   - 对照现有前端页面（知识库管理、文档管理、索引任务等），确认接口返回字段是否满足页面展示需求
   - 分页参数格式：`{ page, page_size }`
   - 响应格式：`{ success, data, message, request_id }`

2. **长任务进度展示**
   - `Document.status` + `processing_error`：文档处理状态和失败原因
   - `IndexTask.progress` + `error_message`：索引任务进度和错误信息

3. **操作影响说明**
   - 发布、下线等操作前展示影响范围（是否影响检索、是否触发问答复核）
   - 使用 ConfirmAction 弹窗展示影响说明

4. **筛选条件对齐**
   - 确认是否需要增加额外筛选条件（按状态、类型、时间范围等）

### 2.3 联调步骤

1. 在 PR 中确认成员5 接口已就绪
2. 将前端页面中 Mock 数据替换为真实 API 调用（`@/api/request.ts` 中的 `api` 实例）
3. 逐页面对比接口响应与前端 `types/admin/` 中的类型定义
4. 发现问题在 PR 或群里反馈，**不自行改后端路由**

---

## 三、与成员4 联调：身份认证与权限系统

### 3.1 成员4 提供的接口

> 来源：成员4 协调方案 第七节

#### 认证接口

| 方法 | 路径 | 描述 | 前端页面 |
|------|------|------|----------|
| POST | `/api/auth/login` | 用户登录 | 登录页 |
| POST | `/api/auth/refresh` | 刷新令牌 | 全局（token自动刷新） |
| POST | `/api/auth/logout` | 退出登录 | 全局 |
| GET | `/api/auth/me` | 当前用户信息 | 全局（权限获取） |
| POST | `/api/auth/reset-password` | 重置密码 | 个人设置 |

#### RBAC 接口

| 方法 | 路径 | 描述 | 前端页面 |
|------|------|------|----------|
| POST | `/api/rbac/permissions` | 创建权限 | 权限管理 |
| GET | `/api/rbac/permissions` | 获取权限列表 | 权限管理 |
| GET | `/api/rbac/permissions/{id}` | 获取权限详情 | 权限编辑 |
| PUT | `/api/rbac/permissions/{id}` | 更新权限 | 权限编辑 |
| DELETE | `/api/rbac/permissions/{id}` | 删除权限 | 权限管理 |
| POST | `/api/rbac/roles` | 创建角色 | 角色管理 |
| GET | `/api/rbac/roles` | 获取角色列表 | 角色管理 |
| GET | `/api/rbac/roles/{id}` | 获取角色详情 | 角色编辑 |
| PUT | `/api/rbac/roles/{id}` | 更新角色 | 角色编辑 |
| DELETE | `/api/rbac/roles/{id}` | 删除角色 | 角色管理 |
| POST | `/api/rbac/users/{user_id}/roles` | 分配角色给用户 | 用户管理 |
| DELETE | `/api/rbac/users/{user_id}/roles/{role_id}` | 移除用户角色 | 用户管理 |
| POST | `/api/rbac/roles/{role_id}/permissions` | 分配权限给角色 | 角色编辑 |
| DELETE | `/api/rbac/roles/{role_id}/permissions/{perm_id}` | 移除角色权限 | 角色编辑 |
| POST | `/api/rbac/permission-check` | 检查权限 | 全局（按钮/菜单控制） |

#### 组织管理接口

| 方法 | 路径 | 描述 | 前端页面 |
|------|------|------|----------|
| POST | `/api/organization/departments` | 创建部门 | 部门管理 |
| GET | `/api/organization/departments` | 获取部门列表 | 部门管理 |
| GET | `/api/organization/departments/tree` | 获取部门树 | 部门管理（树形展示） |
| GET | `/api/organization/departments/{id}` | 获取部门详情 | 部门编辑 |
| PUT | `/api/organization/departments/{id}` | 更新部门 | 部门编辑 |
| DELETE | `/api/organization/departments/{id}` | 删除部门 | 部门管理 |
| POST | `/api/organization/user-groups` | 创建用户组 | 用户组管理 |
| GET | `/api/organization/user-groups` | 获取用户组列表 | 用户组管理 |
| PUT | `/api/organization/user-groups/{id}` | 更新用户组 | 用户组编辑 |
| DELETE | `/api/organization/user-groups/{id}` | 删除用户组 | 用户组管理 |
| POST | `/api/organization/departments/{id}/users` | 分配用户到部门 | 部门编辑 |
| DELETE | `/api/organization/departments/{id}/users/{user_id}` | 移除部门用户 | 部门编辑 |

#### 审计接口

| 方法 | 路径 | 描述 | 前端页面 |
|------|------|------|----------|
| GET | `/api/audit/audit-logs` | 查询审计日志 | 操作日志 |
| GET | `/api/audit/security-events` | 查询安全事件 | 安全事件 |
| POST | `/api/audit/security-events/{id}/resolve` | 标记安全事件已解决 | 安全事件 |
| GET | `/api/audit/login-logs` | 查询登录日志 | 操作日志/登录日志 |

#### 数据权限接口

| 方法 | 路径 | 描述 | 前端页面 |
|------|------|------|----------|
| POST | `/api/data-permission/knowledge-base-permissions` | 创建知识库权限 | 知识库权限 |
| POST | `/api/data-permission/document-permissions` | 创建文档权限 | 文档权限 |
| POST | `/api/data-permission/temporary-grants` | 创建临时授权 | 临时授权 |
| GET | `/api/data-permission/temporary-grants` | 获取临时授权列表 | 临时授权 |
| PUT | `/api/data-permission/temporary-grants/{id}` | 更新临时授权 | 临时授权 |
| DELETE | `/api/data-permission/temporary-grants/{id}` | 删除临时授权 | 临时授权 |

### 3.2 成员3 需要实现的前端功能

#### 3.2.1 登录流程
```
登录页 → POST /api/auth/login → 获取 access_token + refresh_token → 存储到 localStorage
     → GET /api/auth/me → 获取用户信息+权限列表 → 存入 AuthStore
     → 根据权限渲染菜单和页面
```

**数据结构参考**（来自成员4 协调方案）：
```typescript
// 用户信息
interface UserInfo {
  id: string;
  username: string;
  email: string;
  roles: string[];
  permissions: string[];
  tenant_id: string;
}

// 权限检查
interface PermissionCheck {
  action: string;
  resource_type: string;
  resource_id?: string;
}
```

#### 3.2.2 认证状态管理
- 创建 AuthStore（Zustand）管理登录状态
- 实现自动刷新 token 逻辑（`POST /api/auth/refresh`）
- 401 时自动跳转登录页
- Token 过期前自动续期

#### 3.2.3 权限控制体系
- 调用 `GET /api/auth/me` 获取用户权限列表
- 根据权限控制菜单显示/隐藏（使用现有 PermissionGate 组件）
- 按钮级权限：使用 `POST /api/rbac/permission-check` 检查操作权限
- 权限编码规范（来自成员4）：

| 资源类型 | 操作 | 权限编码 |
|----------|------|----------|
| document | create/read/update/delete | `document:create` |
| knowledge_base | manage/read/write | `knowledge_base:manage` |
| user | manage/create/update | `user:manage` |
| role | manage/create/update | `role:manage` |
| permission | manage | `permission:manage` |
| feedback | create/read | `feedback:create` |

#### 3.2.4 待新增/改造的前端页面

| 页面 | 依赖接口 | 当前状态 |
|------|----------|----------|
| 登录页 | `POST /api/auth/login` | **需新建** |
| 用户管理 | RBAC + 组织接口 | 已有（需对接真实API） |
| 角色管理 | RBAC 接口 | 已有（需对接真实API） |
| 部门管理（树形） | 组织接口 `departments/tree` | 已有（需增加树形展示） |
| 用户组管理 | 组织接口 `user-groups` | **需新建** |
| 权限管理 | RBAC permissions 接口 | **需新建** |
| 操作日志 | 审计接口 `audit-logs` | 已有（需对接真实API） |
| 安全事件 | 审计接口 `security-events` | 已有（需对接真实API） |
| 登录日志 | 审计接口 `login-logs` | **需新建** |
| 知识库管理 | 成员5 知识库接口 | 已有（需对接真实API） |
| 文档管理 | 成员5 文档接口 | 已有（需对接真实API） |
| 索引任务 | 成员5 索引任务接口 | 已有（需对接真实API） |

---

## 四、联调依赖关系

```
成员4（身份认证）
    │
    ├──→ 成员3 登录/权限体系（前置依赖，需最先联调）
    │
成员5（文档处理流水线）
    │
    ├──→ 成员3 知识库/文档/Chunk/索引任务页面
    │
成员6（混合检索）
    │
    ├──→ 成员3 检索调试页面（已有占位）
    │
成员7（标准问答）
    │
    ├──→ 成员3 待审核问答页面（已有占位）
```

---

## 五、联调步骤与时间线

### Phase 1：认证体系联调（优先）
1. 成员4 确认认证接口已部署
2. 成员3 实现登录页面 + AuthStore
3. 验证 token 颁发、刷新、过期处理
4. 验证 `GET /api/auth/me` 返回用户权限信息

### Phase 2：权限与组织管理联调
1. 成员4 确认 RBAC + 组织管理接口已部署
2. 成员3 对接用户管理、角色管理、部门管理页面
3. 验证 PermissionGate 组件权限控制正确
4. 验证部门树形结构展示

### Phase 3：知识库与文档联调
1. 成员5 确认知识库/文档接口已部署
2. 成员3 对接知识库管理、文档管理、索引任务页面
3. 验证分页、筛选、状态展示
4. 验证长任务进度和失败原因展示

### Phase 4：审计与安全联调
1. 成员4 确认审计接口已部署
2. 成员3 对接操作日志、安全事件、登录日志页面
3. 验证审计数据分页和筛选

### Phase 5：端到端全链路测试
1. 完整流程：登录 → 权限校验 → 各页面功能 → 操作审计
2. 验证所有 Mock 数据已替换为真实 API
3. 验证错误处理和边界情况

---

## 六、当前 Mock / 阻塞项

以下项不阻塞 PR 评审，但阻塞生产验收：

| 项 | 当前实现 | 依赖 | 预计就绪 |
|----|----------|------|----------|
| 登录认证 | 未实现（Mock 用户） | 成员4 AuthService | Phase 1 |
| 用户/角色/权限CRUD | Mock 数据 | 成员4 RBAC | Phase 2 |
| 部门树形数据 | Mock 数据 | 成员4 组织管理 | Phase 2 |
| 知识库/文档列表 | Mock 数据 | 成员5 知识库接口 | Phase 3 |
| 索引任务状态 | Mock 数据 | 成员5 索引任务 | Phase 3 |
| 审计日志 | Mock 数据 | 成员4 审计服务 | Phase 4 |
| Token 自动刷新 | 未实现 | 成员4 refresh 接口 | Phase 1 |

---

## 七、前端代码规范（联调时遵循）

### API 调用规范
```typescript
// 统一使用 @/api/request.ts 中的 api 实例
import api from '@/api/request';

// 分页参数格式
const params = { page: 1, page_size: 20 };

// 响应格式
interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
  request_id: string;
}
```

### 页面标准结构
```typescript
export function XxxPage() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open, data, show, hide } = useDetailDrawer<Type>();
  const { open: confirmOpen, show: showConfirm, hide: hideConfirm } = useConfirmAction();

  return (<div>
    <div className={styles.pageHeader}>...</div>
    <FilterBar ... />
    <DataTable ... />
    <DetailDrawer ... />
    <ConfirmAction ... />
  </div>);
}
```

### 权限控制
```typescript
// 页面级权限
<PermissionGate permission="user:read">
  <UserManagement />
</PermissionGate>

// 按钮级权限
<PermissionGate permission="user:create">
  <Button>新建用户</Button>
</PermissionGate>
```

---

## 八、签收记录表

| 对接成员 | 事项 | 已通知 | 已回复 | 联调时间 | 备注 |
|----------|------|--------|--------|----------|------|
| 成员4 | 认证/RBAC/组织/审计接口 | ☐ | ☐ | | 前置依赖 |
| 成员5 | 知识库/文档/Chunk/索引接口 | ☐ | ☐ | | |
| 成员6 | 检索调试接口 | ☐ | ☐ | | |
| 成员7 | 待审核问答接口 | ☐ | ☐ | | |

---

## 九、快速启动

```bash
# 1. 同步最新代码
cd C:\code\Claudecode\git-rag\origin
git fetch origin
git pull --ff-only origin develop

# 2. 启动前端开发服务器
cd frontend
npm install
npx vite --host 0.0.0.0 --port 5173

# 3. 修改 API 地址（如需）
# 修改 frontend/.env 或 vite.config.ts 中的代理配置
# 默认代理 /api -> http://localhost:8000
```

---

## 十、参考文档

| 文档 | 路径/链接 |
|------|-----------|
| 成员5 联调操作说明 | `C:\Users\23613\Desktop\member5-联调操作说明.md` |
| 成员4 协调方案 | `C:\Users\23613\Desktop\成员4协调方案.md` |
| 成员5 接口契约 | `docs/member5-contracts.md` |
| 成员3 开发总结 | `C:\Users\23613\Desktop\成员3_管理后台前端_开发总结.md` |
| 本项目 PR | `http://192.168.50.25:3010/admin/origin/pulls` |

---

**文档版本：** v1.0
**维护：** 成员3；接口变更需通知对应成员后更新本文档