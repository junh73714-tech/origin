# 成员3 管理后台前端开发总结

## 一、完成了什么

### 5个里程碑全部完成 (M1-M5)

| 里程碑 | 分支 | 内容 |
|--------|------|------|
| M1 | feature/m3-admin-skeleton | 后台骨架：布局、路由、菜单、11个公共组件、工作台 |
| M2 | feature/m3-admin-pages-1 | 6个页面：用户管理、角色管理、部门管理、知识库管理、文档管理、索引任务 |
| M3 | feature/m3-admin-pages-2 | 2个页面：检索调试（完整链路）、待审核问答 |
| M4 | feature/m3-admin-pages-3 | 4个页面：评估任务、安全事件、操作日志、系统健康 |
| M5 | m3-admin-console | 类型定义对齐成员5 API + 联调操作说明 |

### 交付统计
- **48个文件**变更，**5,591行**新增代码
- **12个**完整页面 + **30+** 占位页面（路由已注册）
- **11个**公共后台组件（DataTable、FilterBar、StatusTag等）
- **8个**自定义Hooks（usePagination、useAsyncData等）
- **200+** 类型定义
- **40+** 路由注册

### M5 新增：类型对齐成员5 API
- 新增 `KnowledgeBase`、`KnowledgeBaseDetail`、`KnowledgeBaseStats`、`KnowledgeBasePermission` 类型
- 新增 `Document`、`DocumentDetail` 类型
- 重写 `DocumentVersion`（+6字段）、`ChunkInfo`/`ChunkDetail`（字段名对齐）、`IndexTask`（+5字段）
- 添加 `docs/m3-integration-guide.md` 联调操作说明

### Gitea PR（已合并为1个）
- **http://192.168.50.25:3010/admin/origin/pulls/14** ← 当前唯一 PR
- 分支：`m3-admin-console` → `develop`
- 旧4个PR（#4/#5/#6/#7）已关闭，合并为此1个PR

---

## 二、踩过的坑

### 1. 文件扩展名问题
**现象**：`.ts` 文件包含 JSX 代码导致 TypeScript 编译报错
**原因**：JSX 语法只能在 `.tsx` 文件中使用
**解决**：将 `routes/index.ts` 改为 `routes/index.tsx`，`pages/admin/index.ts` 改为 `pages/admin/index.tsx`

### 2. 预存的 Layout 命名冲突
**现象**：`Layout.tsx` 中 `import { Layout } from 'antd'` 与 `export function Layout()` 名称冲突
**解决**：改为 `import { Layout as AntLayout } from 'antd'`，用别名避免冲突

### 3. Gitea API 认证
**现象**：直接调用 Gitea API 创建 PR 时报 token 无效
**原因**：Gitea 需要有效的用户 token 或 Basic Auth
**解决**：使用 `git credential fill` 获取存储的凭据，或直接用 `-u 用户名:密码`

### 4. 分支创建策略
**现象**：每个里程碑分支基于上一个里程碑分支创建，形成链式依赖
**注意**：M2 从 M1 创建，M3 从 M2 创建，M4 从 M3 创建。合并时只需合并最后一个分支

### 5. 用户端页面占位
**现象**：路由配置中引用了成员2的页面，但文件不存在导致构建失败
**解决**：创建了最小占位页面，每个页面导出 `Component` 供 React Router lazy 加载

---

## 三、下次注意事项

### Git 协作
1. **每次开发前必须先 `git pull`**，避免冲突
2. **分支命名**：严格遵循 `feature/m3-任务名` 格式
3. **提交粒度**：每个子任务完成后立即提交，不要积压
4. **禁止 `git push --force`**，禁止直接推送到 `main` 或 `develop`
5. **提交信息格式**：`feat(m3): 中文说明` 或 `fix(m3): 中文说明`

### 代码规范
1. **所有文件使用 UTF-8 编码**，注释使用中文简体
2. **组件文件使用 `.tsx` 扩展名**（包含 JSX 时）
3. **纯类型/逻辑文件使用 `.ts` 扩展名**
4. **每个组件文件顶部添加 JSDoc 注释**，说明功能和归属
5. **Mock 数据标注 `// TODO: 替换为真实 API`**，方便后续联调替换

### 组件开发
1. **公共组件**放在 `components/admin/`，页面放在 `pages/admin/`
2. **使用统一组件**：DataTable 替代裸 Table，FilterBar 替代手动筛选
3. **状态标签**统一使用 StatusTag 组件（50+ 状态映射）
4. **高风险操作**必须使用 ConfirmAction 弹窗，展示影响范围
5. **无权限操作**使用 PermissionGate 包裹

### 接口联调
1. 所有页面当前使用 Mock 数据，待后端 API 就绪后替换
2. API 调用统一使用 `@/api/request.ts` 中的 `api` 实例
3. 分页参数格式：`{ page, page_size }`
4. 响应格式：`{ success, data, message, request_id }`

---

## 四、代码规范（下次开发遵循）

### 目录结构
```
frontend/src/
├── types/admin/          # 类型定义（纯类型，.ts文件）
├── stores/admin/         # Zustand 状态管理
├── hooks/admin/          # 自定义 Hooks
├── components/admin/     # 公共组件（.tsx）
├── layouts/admin/        # 布局组件
├── pages/admin/          # 页面组件（.tsx）
└── routes/               # 路由配置（.tsx）
```

### 文件命名
- 组件文件：PascalCase，如 `UserManagement.tsx`
- 样式文件：`ComponentName.module.css`
- 导出索引：`index.ts` 或 `index.tsx`

### 注释规范
```typescript
/**
 * 管理后台 - 用户管理页面
 * 成员3：管理后台前端 - 4.2 用户与组织
 * 用户列表、创建、编辑、启用/禁用
 */
export function UserManagement() { ... }
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

### 主题/样式规范
- 主色：`#1677ff`（亮蓝）
- 圆角：8px
- 背景：`#f5f6f8`（极浅灰）
- 卡片：白色 + `box-shadow: 0 1px 4px rgba(0,0,0,0.06)`
- 引用样式：`import styles from '@/layouts/admin/AdminLayout.module.css';`

---

## 五、环境信息

| 项目 | 信息 |
|------|------|
| 仓库地址 | http://192.168.50.25:3010/admin/origin |
| 当前分支 | m3-admin-console（后续所有修改在此分支） |
| 前端端口 | 5173 |
| 前端框架 | React 18 + TypeScript + Vite + Ant Design 5 |
| 状态管理 | Zustand |
| Gitea 账号 | test / a123456789 |

---

## 六、快速启动

```bash
# 1. 同步最新代码
cd C:\code\Claudecode\git-rag\origin
git fetch origin
git switch m3-admin-console
git pull --ff-only origin develop

# 2. 创建功能分支（如需）
git switch -c feature/m3-新功能名

# 3. 启动前端开发服务器
cd frontend
npm install
npx vite --host 0.0.0.0 --port 5173

# 4. 开发完成后提交
git add <文件>
git commit -m "feat(m3): 功能说明"
git push -u origin feature/m3-新功能名

# 5. 在 Gitea 上创建 PR
# http://192.168.50.25:3010/admin/origin/pulls
```

---

*更新时间：2026-07-17*
*成员3：管理后台前端*