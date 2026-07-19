import { useEffect, useRef } from 'react';
import type { ChatMessage } from '@/types/chat';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';

interface MessageListProps {
  messages: ChatMessage[];
  onRegenerate: () => void;
}

/** 消息列表：长回答滚动与自动定位到底部 */
export function MessageList({ messages, onRegenerate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px' }} aria-label="消息列表">
      {messages.map((m) =>
        m.role === 'user' ? (
          <UserMessage key={m.message_id} content={m.content} />
        ) : (
          <AssistantMessage key={m.message_id} msg={m} onRegenerate={onRegenerate} />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}
