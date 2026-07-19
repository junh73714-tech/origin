// SSE 流式问答 Mock（对齐成员6修订事件契约）。
// 事件序列：message_start -> answer_delta* -> citation* -> metadata -> done。
// answer_delta 载荷使用 { content, done? }；done 载荷使用 { answer, conversation_id, message_id, ... }。
// 根据问题内容触发不同 answer_type：包含"机密/内部工资"触发拒答；
// 包含"不知道/无关"触发证据不足；其余走 RAG 生成并带引用。
import type { StreamController, StreamHandlers } from '@/api/sseClient';
import type {
  AskRequest,
  AnswerType,
  Citation,
  EvidenceStatus,
} from '@/types/chat';

let seq = 500;
function nextId(prefix: string): string {
  seq += 1;
  return `${prefix}-${seq}`;
}

interface Scenario {
  answer_type: AnswerType;
  evidence_status: EvidenceStatus;
  chunks: string[];
  citations: Citation[];
  refusal_reason?: string;
}

function pickScenario(question: string): Scenario {
  const q = question.trim();
  if (/机密|工资|薪酬|内部人事/.test(q)) {
    return {
      answer_type: 'refusal',
      evidence_status: 'none',
      chunks: [],
      citations: [],
      refusal_reason: '该问题涉及无访问权限的受限内容，无法提供答案。',
    };
  }
  // 默认对未命中索引的"测试"类问题模拟证据不足拒答，贴近真实后端行为
  if (/测试|不知道|无关|随便|测试证据不足/.test(q)) {
    return {
      answer_type: 'refusal',
      evidence_status: 'insufficient',
      chunks: [],
      citations: [],
      refusal_reason: '未找到足够有效证据，无法给出确定答案。',
    };
  }
  return {
    answer_type: 'rag',
    evidence_status: 'sufficient',
    chunks: [
      '根据产品使用手册，',
      '您可以在登录页点击"忘记密码"，',
      '系统会向绑定邮箱发送一次性重置链接，',
      '链接有效期为 30 分钟。\n\n',
      '企业统一身份用户请通过内部门户完成重置。',
    ],
    citations: [
      { citation_id: 'cite-001', index: 1, document_name: '产品使用手册', snippet: '密码重置流程' },
      {
        citation_id: 'cite-restricted',
        index: 2,
        document_name: '内部运维手册（受限）',
        snippet: '受限内容',
      },
    ],
  };
}

export const sseMock = {
  streamAsk(payload: AskRequest, handlers: StreamHandlers): StreamController {
    const scenario = pickScenario(payload.content ?? '');
    const messageId = nextId('m');
    const conversationId = payload.conversation_id || nextId('c');
    let aborted = false;
    const timers: ReturnType<typeof setTimeout>[] = [];

    const schedule = (fn: () => void, ms: number) => {
      timers.push(setTimeout(() => !aborted && fn(), ms));
    };

    let t = 200;
    schedule(() => {
      handlers.onEvent({
        event: 'message_start',
        data: { message_id: messageId, conversation_id: conversationId },
      });
    }, t);

    let acc = '';
    scenario.chunks.forEach((chunk) => {
      t += 260;
      schedule(() => {
        acc += chunk;
        // 新契约：answer_delta.data.content
        handlers.onEvent({ event: 'answer_delta', data: { content: chunk } });
      }, t);
    });

    scenario.citations.forEach((citation) => {
      t += 160;
      schedule(() => {
        handlers.onEvent({ event: 'citation', data: { citation } });
      }, t);
    });

    t += 200;
    schedule(() => {
      handlers.onEvent({
        event: 'metadata',
        data: {
          answer_type: scenario.answer_type,
          evidence_status: scenario.evidence_status,
          refusal_reason: scenario.refusal_reason,
        },
      });
    }, t);

    t += 200;
    schedule(() => {
      // 新契约：done.data.answer
      const finalContent =
        scenario.answer_type === 'refusal' ? '' : acc;
      handlers.onEvent({
        event: 'done',
        data: {
          message_id: messageId,
          conversation_id: conversationId,
          answer: finalContent,
          answer_type: scenario.answer_type,
          evidence_status: scenario.evidence_status,
          citations: scenario.citations,
          refusal_reason: scenario.refusal_reason,
        },
      });
      handlers.onClose();
    }, t);

    return {
      abort: () => {
        aborted = true;
        timers.forEach(clearTimeout);
        handlers.onClose();
      },
    };
  },
};
