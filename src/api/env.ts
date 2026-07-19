// 运行时环境标志。Mock 开关决定 API 层走本地 Mock 还是真实后端。
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
