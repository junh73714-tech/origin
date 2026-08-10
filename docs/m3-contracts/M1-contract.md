# M1 管理后台骨架 - 契约文件

## 概述
- **里程碑**: M1 - 管理后台骨架
- **分支**: `feature/m3-admin-skeleton`
- **成员**: 成员3
- **日期**: 2026-07-16
- **状态**: 已完成

## 目录结构

```
frontend/src/
├── types/admin/index.ts              # 200+ 管理后台类型定义
├── stores/admin/index.ts             # Zustand 状态管理
├── hooks/admin/index.ts              # 8个自定义 Hooks
├── components/admin/                 # 11个公共后台组件
│   ├── DataTable.tsx                 # 数据表格
│   ├── FilterBar.tsx                 # 筛选栏
│   ├── StatusTag.tsx                 # 状态标签（50+ 状态映射）
│   ├── DetailDrawer.tsx              # 详情抽屉
│   ├── ConfirmAction.tsx             # 操作确认弹窗
│   ├── PermissionGate.tsx            # 权限门控
│   ├── TaskProgress.tsx              # 任务进度
│   ├── AuditTimeline.tsx             # 审计时间线
│   ├── VersionCompare.tsx            # 版本对比
│   ├── JsonViewer.tsx                # JSON 查看器
│   └── MetricCard.tsx                # 指标卡片
├── layouts/admin/
│   ├── AdminLayout.tsx               # 管理后台布局
│   └── AdminLayout.module.css        # 布局样式
├── pages/admin/
│   ├── Dashboard.tsx                 # 工作台
│   └── index.tsx                     # 40+ 占位页面
└── routes/index.tsx                  # 路由配置
```

## 路由契约（/admin）
40+ 路由已注册，包括：工作台、用户管理、部门管理、角色管理、权限管理、知识库管理、文档管理、问答优化、检索调试、评估中心、安全审计、系统设置

## 主题契约
- 主色: `#1677ff` (亮蓝)
- 圆角: 8px
- 背景: `#f5f6f8` (极浅灰)
- 卡片: 白色 + 柔和阴影

## 验收状态
- [x] 布局、路由、菜单可访问
- [x] 11个公共组件就绪
- [x] 工作台页面展示
- [x] 构建通过
- [x] 界面风格符合规范
- [ ] 与成员4/5 API 联调（M2）
- [ ] 集成测试（M4）