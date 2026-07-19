/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// 说明：正式集成时，代理与公共构建配置由成员1在共享工程中统一维护。
// 本独立工程用于成员2模块的开发与自测，Mock 驱动，可独立运行。
export default defineConfig(({ mode }) => {
  // 读取 .env[.mode]，让 server.proxy 能用 VITE_API_TARGET（vite 不会自动注入到 process.env）
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000';

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5202,
      proxy: {
        // 把 /api 前缀的请求转发到真实后端网关，避免 CORS / 跨域问题
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./tests/setup.ts'],
      include: ['tests/**/*.test.{ts,tsx}'],
      exclude: ['tests/e2e/**', 'node_modules/**'],
      css: false,
    },
  };
});
