# 成员2 Gitea 提交与 PR 操作指引

配合《Gitea七人协作提交与项目合并指南》，给出成员2把本模块并入统一仓库的具体步骤。
分支前缀：`feature/m2-`；目标分支统一为 `develop`，禁止直接推 `main`/`develop`。

## 一、并入统一工程的方式

本工程为独立自测版本。集成到统一仓库时，将以下内容复制到统一工程 `frontend/` 对应目录：

```text
本工程 src/pages/user/         → frontend/src/pages/user/
本工程 src/components/user/     → frontend/src/components/user/
本工程 src/stores/chat/         → frontend/src/stores/chat/
本工程 src/stores/conversation/ → frontend/src/stores/conversation/
本工程 src/hooks/chat/          → frontend/src/hooks/chat/
本工程 src/types/chat/          → frontend/src/types/chat/
本工程 tests/user/             → frontend/tests/user/
```

`src/api/http.ts`、`routes.tsx`、`theme.ts` 属成员1共享范围：**不要覆盖**，改为引用共享实现；如需调整，提 Issue 邀请成员1评审。

## 二、分支与提交（小步、单一子任务）

```bash
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feature/m2-user-chat

git add <本次涉及文件>
git commit -m "feat(m2): 实现用户问答端登录与流式问答"
git push -u origin feature/m2-user-chat
```

建议按里程碑拆多个 PR：
`feature/m2-skeleton`（路由+Store+静态页）→ `feature/m2-auth`（认证会话）→
`feature/m2-chat-sse`（SSE+引用+拒答）→ `feature/m2-feedback`（反馈+测试+文档）。

## 三、同步 develop（禁止 rebase/force）

```bash
git fetch origin
git merge origin/develop
# 仅解决本人文件冲突，重跑 npm run test，再 push
```

## 四、PR 必填（按指南 §6.2）

- 任务来源：成员2，任务书章节；
- 完成内容 / 修改范围；
- 接口或数据模型变化（本模块为纯前端消费，无后端迁移）；
- 环境变量：`VITE_USE_MOCK`、`VITE_API_BASE_URL`（只写变量名，不写密钥）；
- 测试：`npm run typecheck` / `npm run test`（19 通过）/ `npm run build`；
- 联调要求：邀请成员4/6/7（接口）、成员1（共享前端文件）；
- 风险与回滚 + 检查项勾选。

## 五、禁止事项

直接推 main/develop、`git push --force`、`git reset --hard`、`git clean -fd`、
提交真实 `.env`/令牌、修改其他成员主责目录、私改公共 API/枚举/Docker/根依赖。
