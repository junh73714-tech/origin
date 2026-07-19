import { describe, it, expect, beforeEach } from 'vitest';
import { useConversationStore } from '@/stores/conversation/conversationStore';

describe('conversationStore 历史会话', () => {
  beforeEach(async () => {
    useConversationStore.getState().reset();
    await useConversationStore.getState().loadList(1);
  });

  it('加载会话列表', () => {
    expect(useConversationStore.getState().list.length).toBeGreaterThan(0);
    expect(useConversationStore.getState().total).toBeGreaterThan(0);
  });

  it('重命名会话', async () => {
    const first = useConversationStore.getState().list[0];
    await useConversationStore.getState().rename(first.conversation_id, '新的标题');
    const updated = useConversationStore
      .getState()
      .list.find((c) => c.conversation_id === first.conversation_id);
    expect(updated?.title).toBe('新的标题');
  });

  it('删除会话后从列表移除', async () => {
    const before = useConversationStore.getState().list.length;
    const target = useConversationStore.getState().list[0];
    await useConversationStore.getState().remove(target.conversation_id);
    const after = useConversationStore.getState().list.length;
    expect(after).toBe(before - 1);
    expect(
      useConversationStore
        .getState()
        .list.find((c) => c.conversation_id === target.conversation_id),
    ).toBeUndefined();
  });

  it('归档会话更新标记', async () => {
    const target = useConversationStore.getState().list.find((c) => !c.archived);
    if (!target) return;
    await useConversationStore.getState().archive(target.conversation_id, true);
    const updated = useConversationStore
      .getState()
      .list.find((c) => c.conversation_id === target.conversation_id);
    expect(updated?.archived).toBe(true);
  });
});
