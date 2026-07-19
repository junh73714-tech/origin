import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChatStore } from '@/stores/chat/chatStore';

// 验证 SSE 流式：增量合并、以 done 为准、拒答、停止生成。
// sseMock 使用 setTimeout，用假定时器推进。
describe('chatStore SSE 流式问答', () => {
  beforeEach(() => {
    useChatStore.getState().reset();
    vi.useFakeTimers();
  });

  it('普通问题：增量合并且以 done 最终内容为准，携带引用', async () => {
    const send = useChatStore.getState().send;
    await send('如何重置密码');

    await vi.runAllTimersAsync();

    const msgs = useChatStore.getState().messages;
    const assistant = msgs.find((m) => m.role === 'assistant');
    expect(assistant).toBeTruthy();
    expect(assistant?.status).toBe('done');
    expect(assistant?.answer_type).toBe('rag');
    expect(assistant?.content).toContain('重置链接');
    expect(assistant?.citations?.length).toBeGreaterThan(0);
    expect(useChatStore.getState().streaming).toBe(false);
  });

  it('受限问题：返回拒答，无正文内容', async () => {
    await useChatStore.getState().send('查询内部工资机密');
    await vi.runAllTimersAsync();

    const assistant = useChatStore.getState().messages.find((m) => m.role === 'assistant');
    expect(assistant?.answer_type).toBe('refusal');
    expect(assistant?.refusal_reason).toBeTruthy();
    expect(assistant?.content).toBe('');
  });

  it('停止生成：标记为 stopped 并结束 streaming', async () => {
    await useChatStore.getState().send('如何重置密码');
    // 只推进一部分时间，让流式进行中
    await vi.advanceTimersByTimeAsync(400);
    expect(useChatStore.getState().streaming).toBe(true);

    useChatStore.getState().stop();
    const assistant = useChatStore.getState().messages.find((m) => m.role === 'assistant');
    expect(assistant?.status).toBe('stopped');
    expect(useChatStore.getState().streaming).toBe(false);
  });
});
