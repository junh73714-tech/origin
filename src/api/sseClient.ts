// SSE 流式问答客户端（成员6契约修订版）。
// 路径：POST /qa/chat
// 请求体：{ conversation_id: string | null, content: string }
// 事件：
//   - answer_delta → data.content (增量片段), data.done (bool, 是否结束)
//   - done         → data.answer (完整答案), data.conversation_id, data.message_id
//   - error        → 错误事件（可选）
// 由于原生 EventSource 不支持自定义 Header（无法带 Bearer Token），
// 这里使用 fetch + ReadableStream 手动解析 SSE，兼顾鉴权与可中断。
// Mock 模式下改用本地流式模拟器，事件序列与真实契约一致。

import { USE_MOCK } from './env';
import { sseMock } from '@/mocks/sseMock';
import type { AskRequest, SseEvent } from '@/types/chat';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export interface StreamHandlers {
  onEvent: (event: SseEvent) => void;
  onError: (message: string) => void;
  onClose: () => void;
}

export interface StreamController {
  /** 主动停止（用户点击“停止生成”或登出时清理） */
  abort: () => void;
}

/** 解析单条 SSE 报文块为强类型事件。
 * 兼容同一行出现多个字段（event: xxx\ndata: {...}），
 * 以及跨多行 data: 累积（按 SSE 规范以单个空行结束事件）。
 */
function parseSseChunk(raw: string): SseEvent | null {
  const lines = raw.split('\n');
  let eventName = '';
  let dataStr = '';
  for (const line of lines) {
    if (line.startsWith('event:')) eventName = line.slice(6).trim();
    else if (line.startsWith('data:')) {
      // SSE 规范：data: 后必须保留至少一个空格前的字符；这里统一 trim
      dataStr += line.slice(5).trim();
    }
  }
  if (!eventName || !dataStr) return null;
  try {
    const data = JSON.parse(dataStr);
    return { event: eventName, data } as SseEvent;
  } catch {
    return null;
  }
}

export function streamAsk(
  payload: AskRequest,
  token: string | null,
  handlers: StreamHandlers,
): StreamController {
  if (USE_MOCK) {
    return sseMock.streamAsk(payload, handlers);
  }

  const controller = new AbortController();

  // 严格按契约：路径 /qa/chat；请求体字段 content；conversation_id 可为 null
  const body = {
    conversation_id: payload.conversation_id ?? null,
    content: payload.content,
  };

  (async () => {
    try {
      const resp = await fetch(`${BASE_URL}/qa/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        handlers.onError('问答服务暂时不可用，请稍后重试。');
        handlers.onClose();
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // SSE 以空行分隔事件
        let sep: number;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const chunk = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const evt = parseSseChunk(chunk);
          if (evt) handlers.onEvent(evt);
        }
      }
      // 流自然结束；若最后一段没有 \n\n 也尝试解析一次
      if (buffer.trim()) {
        const evt = parseSseChunk(buffer);
        if (evt) handlers.onEvent(evt);
      }
      handlers.onClose();
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') {
        handlers.onClose();
        return;
      }
      handlers.onError('网络中断，回答未完成。可点击重新生成。');
      handlers.onClose();
    }
  })();

  return { abort: () => controller.abort() };
}
