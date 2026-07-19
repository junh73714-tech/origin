import { Button, Space, Tooltip, message } from 'antd';
import {
  CopyOutlined,
  LikeOutlined,
  DislikeOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useState } from 'react';
import { feedbackApi } from '@/api/feedbackApi';
import type { ChatMessage, FeedbackType } from '@/types/chat';
import { CorrectionForm } from './CorrectionForm';

interface FeedbackActionsProps {
  msg: ChatMessage;
}

/** 反馈操作条：复制、点赞、点踩、纠错（成员7接口） */
export function FeedbackActions({ msg }: FeedbackActionsProps) {
  const [voted, setVoted] = useState<FeedbackType | null>(null);
  const [correctionOpen, setCorrectionOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(msg.content);
      message.success('已复制');
    } catch {
      message.error('复制失败');
    }
  };

  const vote = async (type: FeedbackType) => {
    try {
      await feedbackApi.submit({
        message_id: msg.message_id,
        conversation_id: msg.conversation_id,
        feedback_type: type,
      });
      setVoted(type);
      message.success('感谢反馈');
    } catch {
      message.error('反馈提交失败，请稍后重试');
    }
  };

  const submitCorrection = async (text: string) => {
    setSubmitting(true);
    try {
      await feedbackApi.submit({
        message_id: msg.message_id,
        conversation_id: msg.conversation_id,
        feedback_type: 'correction',
        correction_text: text,
      });
      message.success('纠错已提交');
      setCorrectionOpen(false);
    } catch {
      message.error('提交失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Space size="small">
        <Tooltip title="复制">
          <Button size="small" type="text" icon={<CopyOutlined />} onClick={copy} aria-label="复制答案" />
        </Tooltip>
        <Tooltip title="有帮助">
          <Button
            size="small"
            type="text"
            icon={<LikeOutlined />}
            onClick={() => vote('like')}
            disabled={voted !== null}
            aria-label="点赞"
          />
        </Tooltip>
        <Tooltip title="无帮助">
          <Button
            size="small"
            type="text"
            icon={<DislikeOutlined />}
            onClick={() => vote('dislike')}
            disabled={voted !== null}
            aria-label="点踩"
          />
        </Tooltip>
        <Tooltip title="纠错">
          <Button
            size="small"
            type="text"
            icon={<EditOutlined />}
            onClick={() => setCorrectionOpen(true)}
            aria-label="纠错"
          />
        </Tooltip>
      </Space>
      <CorrectionForm
        open={correctionOpen}
        submitting={submitting}
        onCancel={() => setCorrectionOpen(false)}
        onSubmit={submitCorrection}
      />
    </>
  );
}
