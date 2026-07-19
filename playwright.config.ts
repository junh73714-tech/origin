import { defineConfig, devices } from '@playwright/test';

// Playwright 端到端测试配置。运行前需先 `npm run dev` 或由 webServer 自动拉起。
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  fullyParallel: true,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5202',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5202',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
