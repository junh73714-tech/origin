import { Tag } from 'antd';
import type { AnswerType, EvidenceStatus } from '@/types/chat';

interface AnswerStatusProps {
  answerType?: AnswerType;
  evidenceStatus?: EvidenceStatus;
}

/**
 * 颜色映射表（与后端 answer_type / evidence_status 枚举对齐）。
 * 表里查不到的值（极端 case / 新枚举）回退到 default 颜色 + 原文，避免 .color undefined 崩溃。
 */
const ANSWER_TYPE_LABEL: Record<string, { text: string; color: string }> = {
  standard_qa: { text: '标准问答', color: 'green' },
  rag: { text: '知识检索生成', color: 'blue' },
  reference: { text: '参考答案', color: 'gold' },
  refusal: { text: '未作答', color: 'default' },
};

const EVIDENCE_LABEL: Record<string, { text: string; color: string }> = {
  sufficient: { text: '证据充分', color: 'green' },
  insufficient: { text: '证据不足', color: 'orange' },
  conflict: { text: '证据冲突', color: 'red' },
  none: { text: '无证据', color: 'default' },
};

function pickLabel<T extends string>(
  table: Record<string, { text: string; color: string }>,
  key: T | undefined,
): { text: string; color: string } | null {
  if (!key) return null;
  return table[key] ?? { text: key, color: 'default' };
}

/** 展示答案类型与可信度/证据状态 */
export function AnswerStatus({ answerType, evidenceStatus }: AnswerStatusProps) {
  const at = pickLabel(ANSWER_TYPE_LABEL, answerType);
  const ev = pickLabel(EVIDENCE_LABEL, evidenceStatus);
  if (!at && !ev) return null;
  return (
    <div style={{ marginBottom: 6 }}>
      {at ? <Tag color={at.color}>{at.text}</Tag> : null}
      {ev ? <Tag color={ev.color}>{ev.text}</Tag> : null}
    </div>
  );
}
