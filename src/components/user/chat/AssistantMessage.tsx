import { Avatar, Button, Space } from 'antd';
import { RobotOutlined, ReloadOutlined } from '@ant-design/icons';
import { useUiStore } from '@/stores/uiStore';
import type { ChatMessage } from '@/types/chat';
import { AnswerStatus } from './AnswerStatus';
import { StreamingAnswer } from './StreamingAnswer';
import { RefusalNotice } from './RefusalNotice';
import { CitationBadge } from '@/components/user/citation/CitationBadge';
import { FeedbackActions } from '@/components/user/feedback/FeedbackActions';
import { LoadingState } from '@/components/user/common/LoadingState';

interface AssistantMessageProps {
  msg: ChatMessage;
  onRegenerate: () => void;
}

/** 助手消息气泡：状态、流式文本、拒答、引用、反馈、重新生成 */
export function AssistantMessage({ msg, onRegenerate }: AssistantMessageProps) {
  const openCitation = useUiStore((s) => s.openCitation);
  const isRefusal = msg.answer_type === 'refusal';
  const streaming = msg.status === 'streaming' || msg.status === 'pending';

  return (
    <div style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
      <Avatar icon={<RobotOutlined />} style={{ background: '#1f5eff' }} />
      <div
        style={{
          background: '#f5f6fa',
          padding: '10px 14px',
          borderRadius: 8,
          maxWidth: '80%',
          minWidth: 120,
        }}
      >
        <AnswerStatus answerType={msg.answer_type} evidenceStatus={msg.evidence_status} />

        {msg.status === 'pending' ? (
          <LoadingState tip="回答处理中" />
        ) : msg.status === 'error' ? (
          <div>
            <RefusalNotice reason={msg.error_message} />
            <Button
              size="small"
              icon={<ReloadOutlined />}
              style={{ marginTop: 8 }}
              onClick={onRegenerate}
            >
              重新生成
            </Button>
          </div>
        ) : isRefusal ? (
          <RefusalNotice reason={msg.refusal_reason} />
        ) : (
          <StreamingAnswer content={msg.content} streaming={streaming} />
        )}

        {msg.status === 'stopped' ? (
          <div style={{ marginTop: 6, color: '#999' }}>（已停止生成）</div>
        ) : null}

        {msg.citations && msg.citations.length > 0 ? (
          <div style={{ marginTop: 10 }}>
            <Space size={[4, 4]} wrap>
              {msg.citations.map((c) => (
                <CitationBadge key={c.citation_id} citation={c} onOpen={openCitation} />
              ))}
            </Space>
          </div>
        ) : null}

        {msg.status === 'done' && !isRefusal ? (
          <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
            <FeedbackActions msg={msg} />
            <Button
              size="small"
              type="text"
              icon={<ReloadOutlined />}
              onClick={onRegenerate}
            >
              重新生成
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
