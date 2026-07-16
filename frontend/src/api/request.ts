/**
 * Axios 请求封装
 * 统一处理请求拦截、响应拦截、错误处理等
 */
import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { message } from 'antd';

// API 基础 URL
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// 创建 Axios 实例
const request: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 添加请求 ID
    config.headers['X-Request-ID'] = `req_${Date.now()}`;

    // 从 localStorage 获取 token
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse) => {
    // 从响应头获取请求 ID
    const requestId = response.headers['x-request-id'];

    // 如果是文件下载，直接返回
    if (response.config.responseType === 'blob') {
      return response;
    }

    // 统一处理业务响应
    const res = response.data;
    if (res.success) {
      return res;
    }

    // 业务错误
    message.error(res.error?.message || '操作失败');
    return Promise.reject(new Error(res.error?.message || '操作失败'));
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // 处理 401 未授权
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // 尝试刷新 token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: newRefreshToken } = response.data.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', newRefreshToken);

          // 重试原请求
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return request(originalRequest);
        } catch (refreshError) {
          // 刷新失败，跳转到登录页
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        window.location.href = '/login';
      }
    }

    // 处理 403 禁止访问
    if (error.response?.status === 403) {
      message.error('权限不足，无法执行此操作');
    }

    // 处理 404
    if (error.response?.status === 404) {
      message.error('请求的资源不存在');
    }

    // 处理 500
    if (error.response?.status >= 500) {
      message.error('服务器错误，请稍后重试');
    }

    // 网络错误
    if (!error.response) {
      message.error('网络连接失败，请检查网络');
    }

    return Promise.reject(error);
  }
);

// 封装请求方法
export const api = {
  get: <T = any>(url: string, params?: any, config?: AxiosRequestConfig) =>
    request.get<T>(url, { params, ...config }),

  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    request.post<T>(url, data, config),

  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    request.put<T>(url, data, config),

  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    request.patch<T>(url, data, config),

  delete: <T = any>(url: string, params?: any, config?: AxiosRequestConfig) =>
    request.delete<T>(url, { params, ...config }),

  upload: <T = any>(url: string, formData: FormData, onProgress?: (percent: number) => void) =>
    request.post<T>(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    }),
};

export default request;
