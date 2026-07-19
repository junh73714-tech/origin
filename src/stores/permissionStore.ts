// permissionStore：承载成员4返回的权限/数据范围摘要。前端只展示，不做推导。
import { create } from 'zustand';
import { authApi } from '@/api/authApi';
import { registerReset } from './resetBus';
import type { PermissionSummary } from '@/types/auth';

interface PermissionState {
  summary: PermissionSummary | null;
  loading: boolean;
  load: () => Promise<void>;
  reset: () => void;
}

const initial = { summary: null, loading: false };

export const usePermissionStore = create<PermissionState>((set) => {
  registerReset(() => set(initial));
  return {
    ...initial,
    async load() {
      set({ loading: true });
      try {
        const summary = await authApi.permissionSummary();
        set({ summary, loading: false });
      } catch {
        set({ loading: false });
      }
    },
    reset() {
      set(initial);
    },
  };
});
