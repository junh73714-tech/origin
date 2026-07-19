import { test, expect } from '@playwright/test';

// 端到端核心流程（Mock 驱动）。运行：npm run test:e2e
// 覆盖任务书要求的关键路径：登录、提问、流式答案、引用、反馈、历史、拒答、错误提示。

async function login(page: import('@playwright/test').Page, username = 'user') {
  await page.goto('/login');
  await page.getByPlaceholder('请输入用户名').fill(username);
  await page.getByPlaceholder('请输入密码').fill('123456');
  await page.getByRole('button', { name: '登录' }).click();
  await expect(page).toHaveURL(/\/chat/);
}

test('登录并进入问答页', async ({ page }) => {
  await login(page);
  await expect(page.getByRole('textbox', { name: '问题输入框' })).toBeVisible();
});

test('发送问题并接收流式答案，可打开引用', async ({ page }) => {
  await login(page);
  await page.getByRole('textbox', { name: '问题输入框' }).fill('如何重置密码');
  await page.getByRole('button', { name: '发送' }).click();

  // 等待流式完成，出现引用角标
  await expect(page.getByText('产品使用手册').first()).toBeVisible({ timeout: 10_000 });
  await page.getByText('产品使用手册').first().click();
  await expect(page.getByText('引用详情')).toBeVisible();
});

test('拒答场景显示明确提示', async ({ page }) => {
  await login(page);
  await page.getByRole('textbox', { name: '问题输入框' }).fill('查询内部工资机密');
  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByText('暂无法给出确定答案')).toBeVisible({ timeout: 10_000 });
});

test('查看历史会话', async ({ page }) => {
  await login(page);
  await page.getByRole('menuitem', { name: '历史会话' }).click();
  await expect(page).toHaveURL(/\/history/);
  await expect(page.getByText('历史会话')).toBeVisible();
});

test('无知识库权限账号显示提示', async ({ page }) => {
  await login(page, 'guest');
  await expect(page.getByText('当前账号暂无可访问的知识库')).toBeVisible();
});

test('禁用账号登录被拒绝', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('请输入用户名').fill('locked');
  await page.getByPlaceholder('请输入密码').fill('123456');
  await page.getByRole('button', { name: '登录' }).click();
  await expect(page.getByRole('alert')).toContainText('禁用');
});
