import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './mocks/server';

// 所有测试开始前启动 MSW
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// 每个测试后重置 MSW handlers
afterEach(() => server.resetHandlers());

// 所有测试结束后关闭 MSW
afterAll(() => server.close());
