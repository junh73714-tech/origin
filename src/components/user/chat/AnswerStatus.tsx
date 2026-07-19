import { Tag } from 'antd';
import type { AnswerType, EvidenceStatus } from '@/types/chat';

interface AnswerStatusProps {
  answerType?: AnswerType;
  evidenceStatus?: EvidenceStatus;
}

const ANSWER_TYPE_LABEL: Record<AnswerType, { text: string; color: string }> = {
  standard_qa: { text: '标准问答', color: 'green' },
  rag: { text: '知识检索生成', color: 'blue' },
  reference: { text: '参考答案', color: 'gold' },
  refusal: { text: '未作答', color: 'default' },
};

const EVIDENCE_LABEL: Record<EvidenceStatus, { text: string; color: string }> = {
  sufficient: { text: '证据充分', color: 'green' },
  insufficient: { text: '证据不足', color: 'orange' },
  conflict: { text: '证据冲突', color: 'red' },
  none: { text: '无证据', color: 'default' },
};

/** 展示答案类型与可信度/证据状态 */
export function AnswerStatus({ answerType, evidenceStatus }: AnswerStatusProps) {
  if (!answerType && !evidenceStatus) return null;
  return (
    <div style={{ marginBottom: 6 }}>
      {answerType ? (
        <Tag color={ANSWER_TYPE_LABEL[answerType].color}>
          {ANSWER_TYPE_LABEL[answerType].text}
        </Tag>
      ) : null}
      {evidenceStatus ? (
        <Tag color={EVIDENCE_LABEL[evidenceStatus].color}>
          {EVIDENCE_LABEL[evidenceStatus].text}
        </Tag>
      ) : null}
    </div>
  );
}
