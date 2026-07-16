/**
 * 管理后台状态管理
 * 成员3：管理后台前端 - Zustand Store
 * 管理后台全局状态，包括工作台数据、菜单权限、用户管理等
 */
import { create } from 'zustand';
import type {
  DashboardStats,
  TimeRange,
  AdminMenuItem,
  AdminUser,
  Department,
  UserGroup,
  Role,
  Permission,
  PermissionGroup,
  SystemHealth,
} from '@/types/admin';

// ==================== 管理后台 Store 接口 ====================

interface AdminStoreState {
  // ========== 工作台 ==========
  /** 工作台统计数据 */
  dashboardStats: DashboardStats | null;
  /** 当前选中的时间范围 */
  dashboardTimeRange: TimeRange;
  /** 工作台数据加载状态 */
  dashboardLoading: boolean;
  /** 设置工作台数据 */
  setDashboardStats: (stats: DashboardStats) => void;
  /** 设置时间范围 */
  setDashboardTimeRange: (range: TimeRange) => void;
  /** 设置加载状态 */
  setDashboardLoading: (loading: boolean) => void;

  // ========== 菜单权限 ==========
  /** 后台菜单列表（由后端返回，按权限过滤） */
  adminMenus: AdminMenuItem[];
  /** 功能权限编码列表 */
  functionalPermissions: string[];
  /** 设置菜单 */
  setAdminMenus: (menus: AdminMenuItem[]) => void;
  /** 设置功能权限 */
  setFunctionalPermissions: (permissions: string[]) => void;
  /** 检查是否有某个权限 */
  hasPermission: (code: string) => boolean;

  // ========== 用户管理 ==========
  /** 用户列表 */
  users: AdminUser[];
  /** 用户总数 */
  usersTotal: number;
  /** 用户列表加载状态 */
  usersLoading: boolean;
  /** 设置用户列表 */
  setUsers: (users: AdminUser[], total: number) => void;
  /** 设置用户加载状态 */
  setUsersLoading: (loading: boolean) => void;

  // ========== 部门管理 ==========
  /** 部门列表 */
  departments: Department[];
  /** 部门树形数据 */
  departmentTree: Department[];
  /** 部门加载状态 */
  departmentsLoading: boolean;
  /** 设置部门列表 */
  setDepartments: (departments: Department[]) => void;
  /** 设置部门加载状态 */
  setDepartmentsLoading: (loading: boolean) => void;

  // ========== 用户组管理 ==========
  /** 用户组列表 */
  userGroups: UserGroup[];
  /** 用户组加载状态 */
  userGroupsLoading: boolean;
  /** 设置用户组列表 */
  setUserGroups: (groups: UserGroup[]) => void;
  /** 设置用户组加载状态 */
  setUserGroupsLoading: (loading: boolean) => void;

  // ========== 角色管理 ==========
  /** 角色列表 */
  roles: Role[];
  /** 角色加载状态 */
  rolesLoading: boolean;
  /** 设置角色列表 */
  setRoles: (roles: Role[]) => void;
  /** 设置角色加载状态 */
  setRolesLoading: (loading: boolean) => void;

  // ========== 权限管理 ==========
  /** 所有权限列表 */
  allPermissions: Permission[];
  /** 权限分组列表 */
  permissionGroups: PermissionGroup[];
  /** 权限加载状态 */
  permissionsLoading: boolean;
  /** 设置权限列表 */
  setAllPermissions: (permissions: Permission[]) => void;
  /** 设置权限分组 */
  setPermissionGroups: (groups: PermissionGroup[]) => void;
  /** 设置权限加载状态 */
  setPermissionsLoading: (loading: boolean) => void;

  // ========== 系统健康 ==========
  /** 系统健康状态 */
  systemHealth: SystemHealth | null;
  /** 健康状态加载状态 */
  systemHealthLoading: boolean;
  /** 设置系统健康状态 */
  setSystemHealth: (health: SystemHealth) => void;
  /** 设置健康状态加载状态 */
  setSystemHealthLoading: (loading: boolean) => void;

  // ========== 全局 ==========
  /** 重置所有管理后台状态 */
  resetAdminState: () => void;
}

// ==================== 初始状态 ====================

const initialState = {
  dashboardStats: null,
  dashboardTimeRange: 'today' as TimeRange,
  dashboardLoading: false,
  adminMenus: [] as AdminMenuItem[],
  functionalPermissions: [] as string[],
  users: [] as AdminUser[],
  usersTotal: 0,
  usersLoading: false,
  departments: [] as Department[],
  departmentTree: [] as Department[],
  departmentsLoading: false,
  userGroups: [] as UserGroup[],
  userGroupsLoading: false,
  roles: [] as Role[],
  rolesLoading: false,
  allPermissions: [] as Permission[],
  permissionGroups: [] as PermissionGroup[],
  permissionsLoading: false,
  systemHealth: null,
  systemHealthLoading: false,
};

// ==================== 创建 Store ====================

export const useAdminStore = create<AdminStoreState>((set, get) => ({
  ...initialState,

  // 工作台
  setDashboardStats: (stats) => set({ dashboardStats: stats }),
  setDashboardTimeRange: (range) => set({ dashboardTimeRange: range }),
  setDashboardLoading: (loading) => set({ dashboardLoading: loading }),

  // 菜单权限
  setAdminMenus: (menus) => set({ adminMenus: menus }),
  setFunctionalPermissions: (permissions) => set({ functionalPermissions: permissions }),
  hasPermission: (code) => {
    const { functionalPermissions } = get();
    return functionalPermissions.includes(code);
  },

  // 用户管理
  setUsers: (users, total) => set({ users, usersTotal: total }),
  setUsersLoading: (loading) => set({ usersLoading: loading }),

  // 部门管理
  setDepartments: (departments) => set({ departments, departmentTree: departments }),
  setDepartmentsLoading: (loading) => set({ departmentsLoading: loading }),

  // 用户组管理
  setUserGroups: (groups) => set({ userGroups: groups }),
  setUserGroupsLoading: (loading) => set({ userGroupsLoading: loading }),

  // 角色管理
  setRoles: (roles) => set({ roles }),
  setRolesLoading: (loading) => set({ rolesLoading: loading }),

  // 权限管理
  setAllPermissions: (permissions) => set({ allPermissions: permissions }),
  setPermissionGroups: (groups) => set({ permissionGroups: groups }),
  setPermissionsLoading: (loading) => set({ permissionsLoading: loading }),

  // 系统健康
  setSystemHealth: (health) => set({ systemHealth: health }),
  setSystemHealthLoading: (loading) => set({ systemHealthLoading: loading }),

  // 重置
  resetAdminState: () => set(initialState),
}));