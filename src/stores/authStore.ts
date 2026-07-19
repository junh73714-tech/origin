// authStore：登录、Token 刷新、退出、当前用户加载。集中处理认证生命周期。
// 依赖成员4接口（经 authApi），Token 刷新逻辑集中在此，避免散落各处。
import { create } from 'zustand';
import { authApi } from '@/api/authApi';
import { configureAuth } from '@/api/http';
import { USE_MOCK } from '@/api/env';
import { authMock } from '@/mocks/authMock';
import { tokenStore } from './tokenStore';
import { resetAllStores } from './resetBus';
import { mapBackendUser } from '@/types/auth';
import type { CurrentUser, LoginRequest } from '@/types/auth';
import type { ApiError } from '@/types/common';

interface AuthState {
  user: CurrentUser | null;
  authenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (payload: LoginRequest) => Promise<boolean>;
  loadCurrentUser: () => Promise<void>;
  logout: () => Promise<void>;
  /** 认证失效时由 http 拦截器回调：清理并置为未认证 */
  forceLogout: () => void;
}

/**
 * 登录直接调用 authApi.login（内部已 unwrap 并从 data.tokens 取 token）。
 * 这里只负责：存 token、把后端下发的 user 写入 store。
 * 不再额外调用 /auth/me，避免多余往返；如后端未带 user 再回退。
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  authenticated: false,
  loading: false,
  error: null,

  async login(payload) {
    set({ loading: true, error: null });
    try {
      // 后端真实契约：data = { user, tokens }，取 token 从 data.tokens.access_token
      const { user, tokens } = await authApi.login(payload);
      if (!tokens?.access_token) {
        throw {
          code: 'AUTH_PAYLOAD_INVALID',
          message: '登录响应缺少 tokens.access_token',
        } as ApiError;
      }
      tokenStore.set(tokens);
      // 把后端 user 形状映射成前端 CurrentUser
      const mapped = mapBackendUser(user);
      set({ user: mapped, authenticated: true, loading: false });
      return true;
    } catch (e) {
      const err = e as ApiError;
      set({ loading: false, error: err?.message || '登录失败，请重试。' });
      return false;
    }
  },

  async loadCurrentUser() {
    const user = await authApi.currentUser();
    set({ user, authenticated: true });
  },

  async logout() {
    try {
      await authApi.logout();
    } finally {
      tokenStore.clear();
      set({ user: null, authenticated: false, error: null });
      // 切换/退出账号：清空所有业务 Store，杜绝跨账号缓存
      resetAllStores();
    }
  },

  forceLogout() {
    tokenStore.clear();
    set({ user: null, authenticated: false });
    // 切回 Mock 模式时清掉上一会话的状态，避免演示账号串味
    if (USE_MOCK) authMock.resetForTest();
    resetAllStores();
  },
}));

// 向 http 层注入 Token 提供者与刷新/失效回调（集中处理刷新）
configureAuth({
  getToken: () => tokenStore.getAccess(),
  refresh: async () => {
    const rt = tokenStore.getRefresh();
    if (!rt) return null;
    try {
      const pair = await authApi.refresh(rt);
      tokenStore.set(pair);
      return pair.access_token;
    } catch {
      return null;
    }
  },
  onUnauthorized: () => {
    useAuthStore.getState().forceLogout();
  },
});
