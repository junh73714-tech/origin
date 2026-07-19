// Axios 请求封装。
// 说明：正式集成时该封装由成员1在 frontend/src/api/ 统一维护；本工程为成员2独立自测提供等价实现。
// 关键职责：统一 baseURL、注入 Bearer Token、附带 request_id/trace_id、集中处理 401 与错误码。

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';
import type { ApiError } from '@/types/common';
import { ErrorCode } from '@/types/common';

/**
 * 统一响应信封（与后端实测对齐）：
 *   成功：{ success: true, data: T, request_id?, trace_id? }
 *   失败：{ success: false, error: { code, message, details? }, request_id?, trace_id? }
 * FastAPI 422 时：{ detail: [...] }（顶层 detail，不走 envelope）
 */
export interface ApiEnvelope<T> {
  success?: boolean;
  data?: T;
  error?: { code?: string; message?: string; details?: unknown };
  message?: string;
  code?: string;
  request_id?: string;
  trace_id?: string;
  /** FastAPI 422 校验错误 */
  detail?: unknown;
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

/** 生成轻量 request_id（联调时后端会返回权威 trace_id） */
function genRequestId(): string {
  const rand = Math.floor(Math.random() * 1e9).toString(16);
  return `web-${Date.now().toString(16)}-${rand}`;
}

/** Token 提供者 / 失效回调，由 authStore 在启动时注入，避免循环依赖 */
type TokenProvider = () => string | null;
type RefreshHandler = () => Promise<string | null>;
type UnauthorizedHandler = () => void;

let tokenProvider: TokenProvider = () => null;
let refreshHandler: RefreshHandler | null = null;
let unauthorizedHandler: UnauthorizedHandler = () => {};

export function configureAuth(opts: {
  getToken: TokenProvider;
  refresh?: RefreshHandler;
  onUnauthorized?: UnauthorizedHandler;
}): void {
  tokenProvider = opts.getToken;
  refreshHandler = opts.refresh ?? null;
  if (opts.onUnauthorized) unauthorizedHandler = opts.onUnauthorized;
}

export const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 20_000,
});

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenProvider();
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  config.headers.set('X-Request-Id', genRequestId());
  // 诊断日志：联调期保留，登录失败排查期可观察到实际 URL 与 body
  // eslint-disable-next-line no-console
  console.log('[http:req]', config.method?.toUpperCase(), config.url, {
    baseURL: config.baseURL,
    data: config.data,
    params: config.params,
  });
  return config;
});

let refreshing: Promise<string | null> | null = null;

/**
 * 从任意信封中提取 error 文本（兼容多种后端错误形态）。
 * - { error: { message } } ← 后端实测
 * - { message: '...' }     ← 旧约定
 * - { detail: '...' | [{loc, msg}] } ← FastAPI 422
 */
function extractErrorMessage(body: unknown): string {
  if (!body || typeof body !== 'object') return '';
  const obj = body as Record<string, unknown>;
  // 嵌套 error.message（真实后端）
  if (obj.error && typeof obj.error === 'object') {
    const e = obj.error as Record<string, unknown>;
    if (typeof e.message === 'string' && e.message) return e.message;
  }
  // 顶层 message（兼容旧信封）
  if (typeof obj.message === 'string' && obj.message) return obj.message;
  if (typeof obj.msg === 'string' && obj.msg) return obj.msg;
  if (typeof obj.error === 'string' && obj.error) return obj.error;
  // FastAPI 422
  if (Array.isArray(obj.detail)) {
    return obj.detail
      .map((d: unknown) => {
        if (d && typeof d === 'object') {
          const it = d as Record<string, unknown>;
          const loc = Array.isArray(it.loc)
            ? (it.loc as unknown[]).filter((x) => x !== 'body').join('.')
            : '';
          return loc ? `${loc}: ${it.msg ?? ''}` : String(it.msg ?? '');
        }
        return String(d);
      })
      .filter(Boolean)
      .join('；');
  }
  if (typeof obj.detail === 'string' && obj.detail) return obj.detail;
  return '';
}

/** 从任意信封中提取 error code（兼容嵌套 error.code 与顶层 code） */
function extractErrorCode(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') return undefined;
  const obj = body as Record<string, unknown>;
  if (obj.error && typeof obj.error === 'object') {
    const e = obj.error as Record<string, unknown>;
    if (typeof e.code === 'string') return e.code;
  }
  if (typeof obj.code === 'string') return obj.code;
  return undefined;
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const body = error?.response?.data as ApiEnvelope<unknown> | undefined;
    const code = extractErrorCode(body);
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };

    // 401 / Token 过期：尝试静默刷新一次，失败则统一登出
    const isAuthFail =
      status === 401 ||
      code === ErrorCode.UNAUTHORIZED ||
      code === ErrorCode.TOKEN_EXPIRED;

    if (isAuthFail && refreshHandler && !original?._retried) {
      original._retried = true;
      try {
        refreshing = refreshing ?? refreshHandler();
        const newToken = await refreshing;
        refreshing = null;
        if (newToken) {
          original.headers = original.headers ?? {};
          (original.headers as Record<string, string>).Authorization = `Bearer ${newToken}`;
          return http(original);
        }
      } catch {
        refreshing = null;
      }
      unauthorizedHandler();
    } else if (isAuthFail) {
      unauthorizedHandler();
    }

    // 诊断日志：联调期保留
    // eslint-disable-next-line no-console
    console.error('[http]', original?.method?.toUpperCase(), original?.url, {
      status,
      body,
    });

    const messageText = extractErrorMessage(body);
    const apiError: ApiError = {
      code: code || `HTTP_${status ?? 'ERR'}`,
      message:
        messageText ||
        `服务异常（HTTP ${status ?? '??'} ${original?.url ?? ''}）。请稍后重试。`,
      request_id:
        (body && typeof body === 'object'
          ? (body as Record<string, unknown>).request_id
          : undefined) as string | undefined,
      trace_id:
        (body && typeof body === 'object'
          ? (body as Record<string, unknown>).trace_id
          : undefined) as string | undefined,
    };
    return Promise.reject(apiError);
  },
);

/**
 * 解包统一响应信封（与后端实测对齐）。
 * - success === true：返回 data
 * - success === false：抛出 ApiError（携带 error.code/error.message/request_id）
 * - 形态不明：以 HTTP 状态码判定，2xx 视作成功，否则抛 ApiError
 */
export function unwrap<T>(resp: ApiEnvelope<T> | undefined | null): T {
  if (resp && resp.success === true) {
    return resp.data as T;
  }
  if (resp && resp.success === false) {
    const err: ApiError = {
      code: extractErrorCode(resp) || 'UNKNOWN',
      message:
        extractErrorMessage(resp) || '服务异常，请稍后重试。',
      request_id: resp.request_id,
      trace_id: resp.trace_id,
    };
    throw err;
  }
  // 形态不明（理论不应出现）。保留返回 data 容错。
  if (resp && 'data' in resp) return (resp.data as T);
  const err: ApiError = {
    code: 'UNKNOWN',
    message: '服务异常，请稍后重试。',
  };
  throw err;
}
