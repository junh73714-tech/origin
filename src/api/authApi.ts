// 认证 API（成员4契约）。Mock 模式下走本地 mock，实现与真实接口签名一致。
// 5 个认证接口：登录 / 刷新 Token / 退出 / 当前用户 / 密码重置。
// 后端真实契约（实测）：信封 { success, data | error, request_id }
//   登录 data: { user, tokens }，user 字段为 id/username/full_name/...
import { http, unwrap } from './http';
import { USE_MOCK } from './env';
import { authMock } from '@/mocks/authMock';
import type { ApiResponse } from '@/types/common';
import type {
  BackendUser,
  CurrentUser,
  LoginRequest,
  PasswordResetRequest,
  PermissionSummary,
  TokenPair,
} from '@/types/auth';
import { mapBackendUser } from '@/types/auth';

/** 登录接口返回 data 的载荷：同时包含 user 与 tokens（user 暂用后端原始形态） */
export interface LoginPayload {
  user: BackendUser;
  tokens: TokenPair;
}

export const authApi = {
  /**
   * 登录：内部统一处理信封，返回 LoginPayload（含 user 与 tokens）。
   * 真实路径：http.post → unwrap；Mock 路径：mock 直接返回 ApiResponse → unwrap。
   * 上层（authStore）拿到 LoginPayload 后用 mapBackendUser 转为 CurrentUser。
   */
  async login(payload: LoginRequest): Promise<LoginPayload> {
    if (USE_MOCK) {
      const resp = await authMock.login(payload);
      return unwrap<LoginPayload>(resp);
    }
    const { data } = await http.post<ApiResponse<LoginPayload>>(
      '/auth/login',
      payload,
    );
    return unwrap<LoginPayload>(data);
  },

  async refresh(refreshToken: string): Promise<TokenPair> {
    if (USE_MOCK) return authMock.refresh(refreshToken);
    const { data } = await http.post<ApiResponse<TokenPair>>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return unwrap<TokenPair>(data);
  },

  async logout(): Promise<void> {
    if (USE_MOCK) return authMock.logout();
    await http.post('/auth/logout');
  },

  /** 当前用户：后端 /auth/me 仍可能 500，调用方需 catch */
  async currentUser(): Promise<CurrentUser> {
    if (USE_MOCK) return authMock.currentUser();
    const { data } = await http.get<ApiResponse<BackendUser>>('/auth/me');
    return mapBackendUser(unwrap<BackendUser>(data));
  },

  async permissionSummary(): Promise<PermissionSummary> {
    if (USE_MOCK) return authMock.permissionSummary();
    const { data } = await http.get<ApiResponse<PermissionSummary>>('/auth/permissions');
    return unwrap<PermissionSummary>(data);
  },

  async resetPassword(payload: PasswordResetRequest): Promise<void> {
    if (USE_MOCK) return authMock.resetPassword(payload);
    await http.post('/auth/reset-password', payload);
  },
};
