/**
 * 认证相关 API
 */
import { api } from './request';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  phone?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  user: UserResponse;
  tokens: TokenResponse;
}

export const authApi = {
  // 登录
  login: (data: LoginRequest) => api.post<{ data: LoginResponse }>('/auth/login', data),

  // 注册
  register: (data: RegisterRequest) => api.post<{ data: UserResponse }>('/auth/register', data),

  // 刷新令牌
  refresh: (refreshToken: string) =>
    api.post<{ data: TokenResponse }>('/auth/refresh', { refresh_token: refreshToken }),

  // 登出
  logout: () => api.post('/auth/logout'),

  // 获取当前用户
  getCurrentUser: () => api.get<{ data: UserResponse }>('/auth/me'),
};
