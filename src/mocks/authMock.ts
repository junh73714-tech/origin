// 认证 Mock（对齐成员4契约）。演示账号：
//   user / 123456    普通用户，可访问部分知识库
//   guest / 123456   受限用户，无可访问知识库（用于空状态演示）
//   locked / 123456  被禁用账号（用于禁用提示演示）
//   retry / wrong    触发连续登录失败 -> 账号临时锁定（AUTH_LOGIN_LOCKED）
import type {
  BackendUser,
  CurrentUser,
  DataScope,
  Department,
  LoginRequest,
  PasswordResetRequest,
  PermissionSummary,
  TokenPair,
} from '@/types/auth';
import { ErrorCode } from '@/types/common';
import type { ApiError } from '@/types/common';
import type { ApiResponse } from '@/types/common';
import type { LoginPayload } from '@/api/authApi';
import { mapBackendUser } from '@/types/auth';

interface MockAccount {
  password: string;
  /** 以后端 BackendUser 形态存储，登录响应直接下发；currentUser() 时再 map */
  user: BackendUser;
  permissions: PermissionSummary;
  /** 模拟成员4 AUTH_LOGIN_MAX_ATTEMPTS 登录失败计数 */
  failed_attempts: number;
  /** 锁定到期时间戳（ms），0 表示未锁定 */
  locked_until: number;
}

const DEPT_TECH: Department = {
  department_id: 'd-001',
  name: '技术支持部',
  parent_id: 'd-000',
};
const DEPT_GUEST: Department = {
  department_id: 'd-099',
  name: '外部访客',
  parent_id: null,
};

const SCOPE_SELF: DataScope = {
  scope_id: 's-001',
  scope_type: 'self',
  description: '仅本人',
};
const SCOPE_DEPT: DataScope = {
  scope_id: 's-002',
  scope_type: 'department',
  description: '本部门',
};

const ACCOUNTS: Record<string, MockAccount> = {
  user: {
    password: '123456',
    user: {
      id: 'u-1001',
      email: '[email protected]',
      username: 'user',
      full_name: '张晓明',
      phone: null,
      is_active: true,
      is_superuser: false,
      status: 'active',
      department_id: DEPT_TECH.department_id,
      department_name: DEPT_TECH.name,
      roles: ['普通用户'],
    },
    permissions: {
      knowledge_scopes: [
        { knowledge_base_id: 'kb-01', name: '产品使用手册', access_level: '可检索' },
        { knowledge_base_id: 'kb-02', name: '常见问题库', access_level: '可检索' },
      ],
      temporary_grants: [
        {
          grant_id: 'g-01',
          resource_name: '内部运维手册',
          expires_at: '2026-08-01T00:00:00Z',
        },
      ],
      data_scopes: [SCOPE_SELF, SCOPE_DEPT],
      menus: ['chat', 'history', 'profile'],
    },
    failed_attempts: 0,
    locked_until: 0,
  },
  guest: {
    password: '123456',
    user: {
      id: 'u-2002',
      email: '[email protected]',
      username: 'guest',
      full_name: '访客用户',
      phone: null,
      is_active: true,
      is_superuser: false,
      status: 'active',
      department_id: DEPT_GUEST.department_id,
      department_name: DEPT_GUEST.name,
      roles: ['受限访客'],
    },
    permissions: {
      knowledge_scopes: [],
      temporary_grants: [],
      data_scopes: [SCOPE_SELF],
      menus: ['chat', 'history', 'profile'],
    },
    failed_attempts: 0,
    locked_until: 0,
  },
  locked: {
    password: '123456',
    user: {
      id: 'u-3003',
      email: '[email protected]',
      username: 'locked',
      full_name: '停用账号',
      phone: null,
      is_active: false,
      is_superuser: false,
      status: 'disabled',
      department_id: DEPT_GUEST.department_id,
      department_name: DEPT_GUEST.name,
      roles: [],
    },
    permissions: {
      knowledge_scopes: [],
      temporary_grants: [],
      data_scopes: [],
      menus: [],
    },
    failed_attempts: 0,
    locked_until: 0,
  },
};

/** 模拟成员4 AUTH_LOGIN_MAX_ATTEMPTS / AUTH_LOGIN_LOCKOUT_MINUTES */
const MAX_ATTEMPTS = 3;
const LOCKOUT_MS = 5 * 60 * 1000;

let currentUsername: string | null = null;

function delay<T>(value: T, ms = 400): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function makeToken(username: string): TokenPair {
  return {
    access_token: `mock-access-${username}-${Date.now()}`,
    refresh_token: `mock-refresh-${username}`,
    token_type: 'Bearer',
    expires_in: 3600,
  };
}

function reject<T = never>(code: string, message: string): Promise<T> {
  const err: ApiError = { code, message };
  return Promise.reject(err);
}

/** mock 也返回 ApiResponse 信封（与真实后端一致）：
 *  成功：{ success: true, data: { user, tokens } }
 *  失败：直接 reject ApiError（与原行为一致）
 */
export const authMock = {
  async login(payload: LoginRequest): Promise<ApiResponse<LoginPayload>> {
    const account = ACCOUNTS[payload.username];
    if (!account || account.password !== payload.password) {
      if (account) {
        account.failed_attempts += 1;
        if (account.failed_attempts >= MAX_ATTEMPTS) {
          account.locked_until = Date.now() + LOCKOUT_MS;
        }
      }
      return reject<ApiResponse<LoginPayload>>(
        ErrorCode.UNAUTHORIZED,
        '用户名或密码错误。',
      );
    }
    if (account.locked_until > Date.now()) {
      const minutes = Math.ceil((account.locked_until - Date.now()) / 60000);
      return reject<ApiResponse<LoginPayload>>(
        ErrorCode.LOGIN_LOCKED,
        `登录失败次数过多，账号已被锁定约 ${minutes} 分钟。`,
      );
    }
    if (account.user.status === 'disabled') {
      return reject<ApiResponse<LoginPayload>>(
        ErrorCode.ACCOUNT_DISABLED,
        '账号已被禁用，请联系管理员。',
      );
    }
    account.failed_attempts = 0;
    account.locked_until = 0;
    currentUsername = payload.username;
    return delay<ApiResponse<LoginPayload>>({
      success: true,
      data: { user: account.user, tokens: makeToken(payload.username) },
    });
  },

  async refresh(refreshToken: string): Promise<TokenPair> {
    const username = refreshToken.replace('mock-refresh-', '');
    if (!ACCOUNTS[username]) {
      return reject(ErrorCode.UNAUTHORIZED, '会话已失效，请重新登录。');
    }
    currentUsername = username;
    return delay(makeToken(username), 200);
  },

  async logout(): Promise<void> {
    currentUsername = null;
    return delay(undefined as void, 150);
  },

  /** 同步清空会话状态（供 authStore.forceLogout 等同步路径调用） */
  resetForTest(): void {
    currentUsername = null;
    // 同步重置所有账号的失败计数与锁定状态，防止测试/演示间状态串味
    Object.values(ACCOUNTS).forEach((a) => {
      a.failed_attempts = 0;
      a.locked_until = 0;
    });
  },

  async currentUser(): Promise<CurrentUser> {
    if (!currentUsername) {
      return reject(ErrorCode.UNAUTHORIZED, '未登录。');
    }
    // mock 内 user 以 BackendUser 形态存储，currentUser() 时再做映射
    return delay(mapBackendUser(ACCOUNTS[currentUsername].user));
  },

  async permissionSummary(): Promise<PermissionSummary> {
    if (!currentUsername) {
      return reject(ErrorCode.UNAUTHORIZED, '未登录。');
    }
    return delay(ACCOUNTS[currentUsername].permissions);
  },

  async resetPassword(payload: PasswordResetRequest): Promise<void> {
    const account = ACCOUNTS[payload.username];
    if (!account) {
      return reject(ErrorCode.UNAUTHORIZED, '用户不存在。');
    }
    if (!payload.new_password || payload.new_password.length < 6) {
      return reject(ErrorCode.SERVER_ERROR, '新密码长度不能少于 6 位。');
    }
    account.password = payload.new_password;
    account.failed_attempts = 0;
    account.locked_until = 0;
    return delay(undefined as void, 300);
  },
};
