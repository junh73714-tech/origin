# M2 用户权限与文档页面 - 契约文件

## 概述
- **里程碑**: M2 - 用户权限与文档页面
- **分支**: `feature/m3-admin-pages-1`
- **成员**: 成员3
- **日期**: 2026-07-16
- **状态**: 已完成

## 已实现页面（6个）

### 用户管理 (UserManagement)
- 表格列表：用户名、姓名、邮箱、手机号、部门、状态、角色、最后登录
- 功能：创建/编辑用户（弹窗表单）、查看详情（右侧抽屉）、启用/禁用
- 筛选：关键词搜索、状态筛选
- 组件：DataTable + FilterBar + DetailDrawer + ConfirmAction

### 角色管理 (RoleManagement)
- 表格列表：角色名称、编码、描述、类型（系统/自定义）、用户数、权限数
- 功能：创建/编辑角色（权限树分配）、删除（系统角色保护）
- 权限树：用户管理、角色管理、知识库管理、文档管理、问答管理
- 组件：DataTable + FilterBar + DetailDrawer + ConfirmAction + Tree

### 部门管理 (DepartmentManagement)
- 表格列表：部门名称、上级部门、负责人、成员数
- 功能：创建/编辑部门（TreeSelect选择上级）、删除
- 组件：DataTable + FilterBar + ConfirmAction + TreeSelect

### 知识库管理 (AdminKBList)
- 卡片网格布局（3列）：左侧彩色图标 + 名称、描述、文档数
- 功能：创建/编辑知识库（名称、描述、公开/私有）、删除
- 组件：Card + StatusTag + ConfirmAction

### 文档管理 (AdminDocList)
- 表格列表：文件类型图标、文档名称、大小、状态、版本、字符数
- 功能：上传文档（拖拽上传）、查看详情、删除
- 支持格式：PDF、DOCX、XLSX、PPTX、TXT、MD、HTML
- 组件：DataTable + FilterBar + DetailDrawer + ConfirmAction + Upload.Dragger

### 索引任务管理 (IndexTaskManagement)
- 表格列表：文档名称、任务类型、状态、进度条、Chunks统计
- 功能：查看详情（TaskProgress阶段展示）、失败重试
- 筛选：状态、任务类型
- 组件：DataTable + FilterBar + DetailDrawer + TaskProgress

## 依赖API（待联调）
- 成员4: GET/POST/PUT/DELETE /api/v1/admin/users
- 成员4: GET/POST/PUT/DELETE /api/v1/admin/roles
- 成员4: GET/POST/PUT/DELETE /api/v1/admin/departments
- 成员5: GET/POST/PUT/DELETE /api/v1/knowledge-bases
- 成员5: GET/POST/DELETE /api/v1/documents
- 成员5: POST /api/v1/knowledge-bases/:kbId/documents/upload
- 成员5: GET /api/v1/admin/index-tasks

## 验收状态
- [x] 6个页面完整实现
- [x] 构建通过
- [x] 推送到远程分支
- [ ] 与成员4 API 联调
- [ ] 与成员5 API 联调
- [ ] 集成测试