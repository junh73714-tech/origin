/**
 * 全局状态管理
 */
import { create } from 'zustand';

interface GlobalState {
  // 侧边栏
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // 主题
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;

  // 加载状态
  globalLoading: boolean;
  setGlobalLoading: (loading: boolean) => void;
}

export const useGlobalStore = create<GlobalState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  theme: 'light',
  setTheme: (theme) => set({ theme }),

  globalLoading: false,
  setGlobalLoading: (loading) => set({ globalLoading: loading }),
}));
