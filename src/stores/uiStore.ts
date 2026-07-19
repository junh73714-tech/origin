// uiStore：全局 UI 状态（引用抽屉开关、当前查看的引用 id、全局消息）。
import { create } from 'zustand';
import { registerReset } from './resetBus';

interface UiState {
  citationDrawerOpen: boolean;
  activeCitationId: string | null;
  openCitation: (citationId: string) => void;
  closeCitation: () => void;
  reset: () => void;
}

const initial = {
  citationDrawerOpen: false,
  activeCitationId: null as string | null,
};

export const useUiStore = create<UiState>((set) => {
  registerReset(() => set(initial));
  return {
    ...initial,
    openCitation(citationId) {
      set({ citationDrawerOpen: true, activeCitationId: citationId });
    },
    closeCitation() {
      set({ citationDrawerOpen: false, activeCitationId: null });
    },
    reset() {
      set(initial);
    },
  };
});
