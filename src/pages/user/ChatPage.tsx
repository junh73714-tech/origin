import { useEffect, useState } from 'react';
import { Card, Space, Tag, Typography, Alert } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { useChatStore } from '@/stores/chat/chatStore';
import { usePermissionStore } from '@/stores/permissionStore';
import { feedbackApi } from '@/api/feedbackApi';
import { MessageList } from '@/components/user/chat/MessageList';
import { ChatComposer } from '@/components/user/chat/ChatComposer';
import { EmptyState } from '@/components/user/common/EmptyState';
import type { RecommendedQuestion } from '@/types/chat';

/** 问答会话页：兼容 /chat 与 /chat/:conversationId */
export function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const messages = useChatStore((s) => s.messages);
  const streaming = useChatStore((s) => s.streaming);
  const send = useChatStore((s) => s.send);
  const stop = useChatStore((s) => s.stop);
  const regenerate = useChatStore((s) => s.regenerate);
  const loadConversation = useChatStore((s) => s.loadConversation);
  const startNew = useChatStore((s) => s.startNewConversation);
  const storeConversationId = useChatStore((s) => s.conversationId);

  const permission = usePermissionStore((s) => s.summary);
  const [recommended, setRecommended] = useState<RecommendedQuestion[]>([]);

  const noKnowledge =
    permission !== null && permission.knowledge_scopes.length === 0;

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else {
      startNew();
    }
  }, [conversationId, loadConversation, startNew]);

  useEffect(() => {
    feedbackApi.recommendedQuestions().then(setRecommended).catch(() => setRecommended([]));
  }, []);

  // 新建会话后，若 store 产生了会话 id，同步到路由
  useEffect(() => {
    if (!conversationId && storeConversationId) {
      navigate(`/chat/${storeConversationId}`, { replace: true });
    }
  }, [conversationId, storeConversationId, navigate]);

  const empty = messages.length === 0;

  return (
    <Card
      styles={{ body: { display: 'flex', flexDirection: 'column', height: 'calc(100vh - 128px)' } }}
    >
      {noKnowledge ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="当前账号暂无可访问的知识库"
          description="您可以提问，但系统可能因无授权知识范围而无法作答。请联系管理员申请权限。"
        />
      ) : null}

      {empty ? (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <EmptyState description="有什么可以帮您？在下方输入问题开始对话。" />
          {recommended.length > 0 ? (
            <div style={{ padding: '0 24px' }}>
              <Typography.Text type="secondary">推荐问题</Typography.Text>
              <div style={{ marginTop: 8 }}>
                <Space size={[8, 8]} wrap>
                  {recommended.map((q) => (
                    <Tag
                      key={q.id}
                      color="blue"
                      style={{ cursor: 'pointer', padding: '4px 10px' }}
                      onClick={() => send(q.text)}
                    >
                      {q.text}
                    </Tag>
                  ))}
                </Space>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <MessageList messages={messages} onRegenerate={regenerate} />
      )}

      <div style={{ paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
        <ChatComposer disabled={false} streaming={streaming} onSend={send} onStop={stop} />
      </div>
    </Card>
  );
}
