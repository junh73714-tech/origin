// conversationStore：历史会话列表、当前会话选择、增删改归档。位于 stores/conversation/。
import { create } from 'zustand';
import { conversationApi } from '@/api/conversationApi';
import { registerReset } from '@/stores/resetBus';
import type { Conversation } from '@/types/chat';

interface ConversationState {
  list: Conversation[];
  total: number;
  page: number;
  pageSize: number;
  keyword: string;
  loading: boolean;
  currentId: string | null;
  setKeyword: (kw: string) => void;
  loadList: (page?: number) => Promise<void>;
  createConversation: (title?: string) => Promise<Conversation>;
  rename: (id: string, title: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  archive: (id: string, archived: boolean) => Promise<void>;
  setCurrent: (id: string | null) => void;
  reset: () => void;
}

const initial = {
  list: [] as Conversation[],
  total: 0,
  page: 1,
  pageSize: 20,
  keyword: '',
  loading: false,
  currentId: null as string | null,
};

export const useConversationStore = create<ConversationState>((set, get) => {
  registerReset(() => set(initial));
  return {
    ...initial,

    setKeyword(kw) {
      set({ keyword: kw });
    },

    async loadList(page = 1) {
      set({ loading: true });
      try {
        const res = await conversationApi.list({
          page,
          page_size: get().pageSize,
          keyword: get().keyword || undefined,
        });
        set({
          list: res.items,
          total: res.total,
          page: res.page,
          loading: false,
        });
      } catch {
        set({ loading: false });
      }
    },

    async createConversation(title) {
      const conv = await conversationApi.create(title);
      set({ list: [conv, ...get().list], currentId: conv.conversation_id });
      return conv;
    },

    async rename(id, title) {
      await conversationApi.rename(id, title);
      set({
        list: get().list.map((c) =>
          c.conversation_id === id ? { ...c, title } : c,
        ),
      });
    },

    async remove(id) {
      await conversationApi.remove(id);
      set({
        list: get().list.filter((c) => c.conversation_id !== id),
        currentId: get().currentId === id ? null : get().currentId,
      });
    },

    async archive(id, archived) {
      await conversationApi.archive(id, archived);
      set({
        list: get().list.map((c) =>
          c.conversation_id === id ? { ...c, archived } : c,
        ),
      });
    },

    setCurrent(id) {
      set({ currentId: id });
    },

    reset() {
      set(initial);
    },
  };
});
