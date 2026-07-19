# 成员2：用户问答端前端

企业级混合检索 RAG 知识问答平台 —— 普通用户使用的问答前端模块。

本工程为成员2模块的**独立可运行实现**，采用 Mock 驱动，可在成员4/6/7 后端尚未就绪时独立开发、演示与自测。正式集成时按任务书将代码并入统一前端工程 `frontend/` 的成员2主责目录，公共路由、Axios、主题由成员1维护。

## 技术栈

React 18 + TypeScript（严格模式）+ Vite 5 + Ant Design 5 + React Router 6 + Zustand 4 + Axios + Vitest + Playwright。

## 目录结构（对应任务书主责目录）

```text
src/
├─ api/                     请求封装、鉴权注入、SSE 客户端、各服务 API（对应共享 frontend/src/api）
├─ mocks/                   认证/会话/引用/反馈 Mock + SSE 流式模拟器
├─ types/
│  ├─ common.ts / auth.ts   公共契约与认证类型（对齐 docs/api-contracts.md）
│  └─ chat/                 会话、消息、引用、SSE 事件、反馈类型【成员2主责】
├─ stores/
│  ├─ authStore / permissionStore / uiStore / tokenStore / resetBus
│  ├─ chat/                 chatStore：流式问答核心状态【成员2主责】
│  └─ conversation/         conversationStore：历史会话【成员2主责】
├─ hooks/chat/              引用详情加载 Hook【成员2主责】
├─ components/user/         auth / chat / citation / conversation / feedback / common【成员2主责】
├─ pages/user/             登录、布局、问答、历史、个人信息【成员2主责】
├─ utils/                   Markdown 安全渲染（防 XSS）、时间格式化
├─ routes.tsx / App.tsx / main.tsx / theme.ts
tests/
├─ user/                    Vitest 单元与组件测试【成员2主责】
└─ e2e/                     Playwright 端到端核心流程
```

## 快速开始

```bash
npm install
cp .env.example .env      # 默认 VITE_USE_MOCK=true，走本地 Mock
npm run dev               # http://localhost:5202
```

### 演示账号

| 账号 | 密码 | 说明 |
|---|---|---|
| user | 123456 | 普通用户，可访问 2 个知识库 |
| guest | 123456 | 无可访问知识库（演示空状态提示） |

> 演示账号需在真后端预创建（通过 `POST /api/v1/auth/register` 或由后端 seed）。禁用账号与连续输错锁定的演示由本地 Mock 模式（`VITE_USE_MOCK=true`）支持；当前真实后端暂未实现锁定接口。

### 演示问答场景（Mock）

- 普通问题（如“如何重置密码”）：RAG 流式回答 + 2 条引用（含 1 条无权限引用）；
- 含“机密/工资”等词：触发**拒答（无权限）**；
- 含“不知道/证据不足”等词：触发**拒答（证据不足）**。

## 常用命令

```bash
npm run dev         # 开发服务器
npm run typecheck   # 严格类型检查
npm run test        # Vitest 单元/组件测试（19 用例）
npm run test:e2e    # Playwright 端到端（需可启动 dev server）
npm run build       # 生产构建
```

## 与后端联调（切换真实接口）

将 `.env` 中 `VITE_USE_MOCK` 改为 `false`，并配置 `VITE_API_BASE_URL` 指向成员1提供的网关。API 层（`src/api/*Api.ts`）已按契约实现真实请求分支，Mock 与真实接口**签名一致、字段一致**，无需改动组件。

依赖接口：
- 成员4：登录、刷新 Token、退出、当前用户、权限/数据范围摘要；
- 成员6：会话创建/获取、SSE 流式问答、停止/重新生成、引用详情；
- 成员7：点赞、点踩、纠错、推荐问题。

## 安全与权限约束（已落实）

- 前端不做权限判断与 RAG 业务判断，只展示后端结果；
- Token 仅存内存，不写入 LocalStorage；切换/退出账号清空全部 Store，杜绝跨账号缓存；
- 引用仅凭 `citation_id` 取详情，无权限不展示真实地址与正文，不暴露 Chunk/DB ID 与存储路径；
- Markdown 经 DOMPurify 净化防 XSS，外部链接强制 `rel="noopener noreferrer"`；
- 401/Token 过期集中处理：静默刷新一次，失败统一登出跳登录页；
- 全中文界面，无 Emoji。

## 相关文档

- `docs/验收清单.md`：逐条对应任务书验收标准；
- `docs/已知问题与技术债务.md`。
