import { Avatar } from 'antd';
import { UserOutlined } from '@ant-design/icons';

interface UserMessageProps {
  content: string;
}

/** 用户消息气泡 */
export function UserMessage({ content }: UserMessageProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, margin: '12px 0' }}>
      <div
        style={{
          background: '#1f5eff',
          color: '#fff',
          padding: '8px 12px',
          borderRadius: 8,
          maxWidth: '72%',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {content}
      </div>
      <Avatar icon={<UserOutlined />} />
    </div>
  );
}
