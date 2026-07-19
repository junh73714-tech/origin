// chatStore：当前会话的消息列表与流式问答核心状态。位于 stores/chat/。
// 关键要求：
//  - 区分流式中间态与最终态，以 done 事件的完整结果为准；
//  - 停止生成、重新生成、失败可重试；
//  - 登出/切换用户时清理 SSE 连接与消息缓存（reset）。
import { create } from 'zustand';
import { streamAsk, type StreamController } from '@/api/sseClient';
import { conversationApi } from '@/api/conversationApi';
import { tokenStore } from '@/stores/tokenStore';
import { registerReset } from '@/stores/resetBus';
import type { ChatMessage, SseEvent } from '@/types/chat';

let msgSeq = 0;
function localId(prefix: string): string {
  msgSeq += 1;
  return `${prefix}-local-${msgSeq}`;
}

interface ChatState {
  conversationId: string | null;
  messages: ChatMessage[];
  streaming: boolean;
  controller: StreamController | null;
  /** 加载已有会话的历史消息 */
  loadConversation: (conversationId: string) => Promise<void>;
  /** 开始新会话（清空当前消息） */
  startNewConversation: () => void;
  /** 发送问题并接入 SSE 流式回答 */
  send: (question: string) => Promise<void>;
  /** 停止生成 */
  stop: () => void;
  /** 重新生成：以最后一条用户问题重发 */
  regenerate: () => Promise<void>;
  /** 重试失败消息 */
  retry: (userMessageId: string) => Promise<void>;
  reset: () => void;
}

const initial = {
  conversationId: null as string | null,
  messages: [] as ChatMessage[],
  streaming: false,
  controller: null as StreamController | null,
};

export const useChatStore = create<ChatState>((set, get) => {
  registerReset(() => {
    get().controller?.abort();
    set(initial);
  });

  /** 更新指定消息 */
  function patchMessage(id: string, patch: Partial<ChatMessage>) {
    set({
      messages: get().messages.map((m) =>
        m.message_id === id ? { ...m, ...patch } : m,
      ),
    });
  }

  /** 执行一次流式问答（内部复用） */
  function runStream(question: string, assistantId: string) {
    const controller = streamAsk(
      { conversation_id: get().conversationId ?? null, content: question },
      tokenStore.getAccess(),
      {
        onEvent: (evt: SseEvent) => handleSseEvent(evt, assistantId),
        onError: (message) => {
          patchMessage(assistantId, { status: 'error', error_message: message });
        },
        onClose: () => {
          set({ streaming: false, controller: null });
          // 若结束时仍处于 streaming（异常关闭），标记为错误可重试
          const msg = get().messages.find((m) => m.message_id === assistantId);
          if (msg && msg.status === 'streaming') {
            patchMessage(assistantId, {
              status: 'error',
              error_message: '回答意外中断，请重新生成。',
            });
          }
        },
      },
    );
    set({ streaming: true, controller });
  }

  function handleSseEvent(evt: SseEvent, assistantId: string) {
    const cur = get().messages.find((m) => m.message_id === assistantId);
    // 一次性下发的"完整消息"（event: message 或 done.data.answer）已包含全文时，
    // 后续到达的同内容 answer_delta 应被丢弃，避免重复拼接。
    const alreadyFinal = cur?.status === 'done' && (cur?.content ?? '').length > 0;

    switch (evt.event) {
      case 'message_start': {
        // data: { conversation_id, message_id, trace_id, answer_type?, query_id? }
        set({ conversationId: evt.data.conversation_id });
        patchMessage(assistantId, {
          conversation_id: evt.data.conversation_id,
          status: 'streaming',
          answer_type: evt.data.answer_type,
        });
        break;
      }
      case 'message': {
        // data: { content, done, references[] } —— 一次性完整消息（拒答/短答）
        // 真实后端会同时再发一条相同内容的 answer_delta；这里记下"已收完整文"标记
        // 让后续 answer_delta 不再追加。
        const refs = evt.data.references ?? [];
        const content = evt.data.content ?? '';
        if (alreadyFinal) break;
        if (content) {
          patchMessage(assistantId, {
            content,
            citations: refs.length ? refs : undefined,
            status: evt.data.done ? 'done' : 'streaming',
          });
        } else if (refs.length) {
          patchMessage(assistantId, {
            citations: refs,
            status: evt.data.done ? 'done' : 'streaming',
          });
        } else if (evt.data.done) {
          patchMessage(assistantId, { status: 'done' });
        }
        break;
      }
      case 'answer_delta': {
        // data: { content, done? } —— 增量片段
        // 若 message_start 或 message 已经下发完整 content（status=done），丢弃重复 delta
        if (alreadyFinal) {
          if (evt.data.done) patchMessage(assistantId, { status: 'done' });
          break;
        }
        const piece = evt.data.content ?? '';
        if (!piece) {
          if (evt.data.done) patchMessage(assistantId, { status: 'done' });
          break;
        }
        patchMessage(assistantId, {
          content: (cur?.content ?? '') + piece,
          status: evt.data.done ? 'done' : 'streaming',
        });
        break;
      }
      case 'citation': {
        if (alreadyFinal) break;
        const list = cur?.citations ? [...cur.citations] : [];
        list.push(evt.data.citation);
        patchMessage(assistantId, { citations: list });
        break;
      }
      case 'metadata': {
        // data: { refusal_reason?, query_id?, answer_type?, ... }
        const patch: Partial<ChatMessage> = {};
        if (evt.data.answer_type) patch.answer_type = evt.data.answer_type;
        if (evt.data.refusal_reason) patch.refusal_reason = evt.data.refusal_reason;
        patchMessage(assistantId, patch);
        break;
      }
      case 'error':
        patchMessage(assistantId, {
          status: 'error',
          error_message: evt.data.message || '回答生成失败。',
        });
        break;
      case 'done': {
        // POST 流中可能 data 为空；GET 流中含完整 { answer, citations, ... }
        const d = evt.data ?? {};
        const final =
          (d as { answer?: string }).answer ??
          (d as { content?: string }).content ??
          '';
        const patch: Partial<ChatMessage> = { status: 'done' };
        if (final && !alreadyFinal) patch.content = final;
        if (d.answer_type) patch.answer_type = d.answer_type;
        if (d.evidence_status) patch.evidence_status = d.evidence_status;
        if (d.citations && d.citations.length) patch.citations = d.citations;
        if (d.refusal_reason) patch.refusal_reason = d.refusal_reason as string;
        patchMessage(assistantId, patch);
        break;
      }
    }
  }

  return {
    ...initial,

    async loadConversation(conversationId) {
      get().controller?.abort();
      set({ conversationId, messages: [], streaming: false, controller: null });
      const detail = await conversationApi.detail(conversationId);
      set({ messages: detail.messages });
    },

    startNewConversation() {
      get().controller?.abort();
      set({ conversationId: null, messages: [], streaming: false, controller: null });
    },

    async send(question) {
      const trimmed = question.trim();
      if (!trimmed || get().streaming) return;

      const userMsg: ChatMessage = {
        message_id: localId('u'),
        conversation_id: get().conversationId ?? '',
        role: 'user',
        content: trimmed,
        status: 'done',
        created_at: new Date().toISOString(),
      };
      const assistantMsg: ChatMessage = {
        message_id: localId('a'),
        conversation_id: get().conversationId ?? '',
        role: 'assistant',
        content: '',
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      set({ messages: [...get().messages, userMsg, assistantMsg] });
      runStream(trimmed, assistantMsg.message_id);
    },

    stop() {
      // 先将流式中的消息标记为 stopped，再中断连接；
      // 避免 abort 触发的 onClose 将其误判为 error。
      const streamingMsg = [...get().messages]
        .reverse()
        .find((m) => m.role === 'assistant' && m.status === 'streaming');
      if (streamingMsg) {
        patchMessage(streamingMsg.message_id, { status: 'stopped' });
      }
      get().controller?.abort();
      set({ streaming: false, controller: null });
    },

    async regenerate() {
      const lastUser = [...get().messages]
        .reverse()
        .find((m) => m.role === 'user');
      if (!lastUser || get().streaming) return;
      const assistantMsg: ChatMessage = {
        message_id: localId('a'),
        conversation_id: get().conversationId ?? '',
        role: 'assistant',
        content: '',
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      set({ messages: [...get().messages, assistantMsg] });
      runStream(lastUser.content, assistantMsg.message_id);
    },

    async retry(userMessageId) {
      const userMsg = get().messages.find((m) => m.message_id === userMessageId);
      if (!userMsg || get().streaming) return;
      const assistantMsg: ChatMessage = {
        message_id: localId('a'),
        conversation_id: get().conversationId ?? '',
        role: 'assistant',
        content: '',
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      set({ messages: [...get().messages, assistantMsg] });
      runStream(userMsg.content, assistantMsg.message_id);
    },

    reset() {
      get().controller?.abort();
      set(initial);
    },
  };
});
