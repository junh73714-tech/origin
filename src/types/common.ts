// 公共类型：与后端 /openapi.json 中的实际响应信封对齐。
// 后端真实信封（成员4/成员6 后端实测）：
//   成功：{ success: true, data: T, request_id?: string, trace_id?: string }
//   失败：{ success: false, error: { code: string, message: string, details?: any }, request_id?: string, trace_id?: string }
// 失败时 HTTP status 通常是 4xx；FastAPI 422 校验失败为 { detail: [...] }。

/** 后端真实错误载荷（嵌套在 envelope.error 下） */
export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

/**
 * 统一 API 响应信封：
 *   成功：{ success: true, data: T, request_id?, trace_id? }
 *   失败：{ success: false, error: ApiErrorBody, request_id?, trace_id? }
 */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiErrorBody;
  request_id?: string;
  trace_id?: string;
}

/** 统一错误结构（供拦截器解析，绝不向页面透出堆栈） */
export interface ApiError {
  code: string;
  message: string;
  request_id?: string;
  trace_id?: string;
}

/** 分页请求参数 */
export interface PageQuery {
  page: number;
  page_size: number;
  keyword?: string;
}

/** 分页响应 */
export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** 统一错误码（子集，前端仅用于分支展示，不做权限推导） */
export const ErrorCode = {
  SUCCESS: '0',
  UNAUTHORIZED: 'AUTH_401', // 未认证或 Token 失效
  TOKEN_EXPIRED: 'AUTH_TOKEN_EXPIRED',
  ACCOUNT_DISABLED: 'AUTH_ACCOUNT_DISABLED', // 账号被禁用
  ACCOUNT_LOCKED: 'AUTH_ACCOUNT_LOCKED', // 连续登录失败被临时锁定
  LOGIN_LOCKED: 'AUTH_LOGIN_LOCKED', // 登录态已锁定（成员4 login lockout）
  FORBIDDEN: 'PERM_403', // 无权限
  EVIDENCE_INSUFFICIENT: 'RAG_EVIDENCE_INSUFFICIENT', // 证据不足
  CITATION_FORBIDDEN: 'CITATION_FORBIDDEN', // 无权查看引用原文
  SERVER_ERROR: 'SERVER_500',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
} as const;

export type ErrorCodeValue = (typeof ErrorCode)[keyof typeof ErrorCode];
