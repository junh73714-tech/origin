// 认证与用户/权限相关类型，依赖成员4接口契约。
// 前端不做权限判断，仅承载后端计算结果。
// 类型命名对齐成员4模型：Department / UserGroup / DataScope / TemporaryGrant /
//   KnowledgeBasePermission / DocumentPermission / LoginLog。

/** 部门（成员4 Department 模型，前端仅承载展示字段） */
export interface Department {
  department_id: string;
  name: string;
  parent_id: string | null;
}

/** 用户组（成员4 UserGroup 模型） */
export interface UserGroup {
  group_id: string;
  name: string;
}

/** 数据范围（成员4 DataScope 模型） */
export interface DataScope {
  scope_id: string;
  scope_type: 'all' | 'department' | 'department_and_sub' | 'self' | 'custom';
  description?: string;
}

/** 临时授权（成员4 TemporaryGrant 模型，前端只读） */
export interface TemporaryGrant {
  grant_id: string;
  resource_name: string;
  expires_at: string; // ISO8601
}

/** 登录日志（成员4 LoginLog 模型，前端用于展示最近登录历史） */
export interface LoginLog {
  log_id: string;
  login_at: string; // ISO8601
  ip: string;
  device: string;
  success: boolean;
}

/** 登录请求 */
export interface LoginRequest {
  username: string;
  password: string;
}

/** 登录/刷新返回的令牌对 */
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string; // 通常 "Bearer"
  expires_in: number; // access_token 有效秒数
}

/** 账号状态（成员4账户禁用 / 锁定区分，对应 AUTH_ACCOUNT_DISABLED / AUTH_ACCOUNT_LOCKED） */
export type AccountStatus = 'active' | 'disabled' | 'locked';

/** 当前用户信息（前端展示用，由后端响应映射而来） */
export interface CurrentUser {
  user_id: string;
  username: string;
  display_name: string;
  department: Department;
  user_groups: UserGroup[];
  roles: string[];
  account_status: AccountStatus;
  /** 后端原始字段，便于调试；不影响 UI */
  email?: string;
  full_name?: string;
}

/** 后端 /auth/login 与 /auth/me 返回的 user 原始载荷（实测字段） */
export interface BackendUser {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  phone?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
  status?: 'active' | 'disabled' | 'locked' | string;
  last_login_at?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  roles?: Array<{ id?: string; name?: string; code?: string }> | string[];
  permissions?: Array<{ id?: string; code?: string; name?: string }> | string[];
  data_scopes?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  [k: string]: unknown;
}

/** 把后端 user 载荷映射到前端 CurrentUser（兼容空值） */
export function mapBackendUser(u: BackendUser | null | undefined): CurrentUser {
  if (!u) {
    return {
      user_id: '',
      username: '',
      display_name: '',
      department: { department_id: '', name: '', parent_id: null },
      user_groups: [],
      roles: [],
      account_status: 'active',
    };
  }
  const roles: string[] = Array.isArray(u.roles)
    ? u.roles.map((r) =>
        typeof r === 'string' ? r : r?.name ?? r?.code ?? r?.id ?? '',
      )
    : [];
  return {
    user_id: u.id ?? '',
    username: u.username ?? '',
    display_name: u.full_name ?? u.username ?? '',
    department: {
      department_id: u.department_id ?? '',
      name: u.department_name ?? '',
      parent_id: null,
    },
    user_groups: [],
    roles,
    account_status:
      (u.status as AccountStatus) ?? (u.is_active === false ? 'disabled' : 'active'),
    email: u.email,
    full_name: u.full_name ?? undefined,
  };
}

/** 单个可访问知识库摘要（后端计算，前端只展示） */
export interface KnowledgeScopeItem {
  knowledge_base_id: string;
  name: string;
  access_level: string; // 例如 只读 / 可检索
}

/** 数据权限 / 权限摘要（对齐成员4 KnowledgeBasePermission 摘要） */
export interface PermissionSummary {
  knowledge_scopes: KnowledgeScopeItem[];
  temporary_grants: TemporaryGrant[];
  data_scopes: DataScope[];
  menus: string[]; // 功能菜单标识，仅用于体验，不替代后端鉴权
}

/** 密码重置请求（成员4 /auth/reset-password 接口） */
export interface PasswordResetRequest {
  username: string;
  /** 新密码；前端不在本地存储旧密码，仅由登录态触发重置 */
  new_password: string;
}
