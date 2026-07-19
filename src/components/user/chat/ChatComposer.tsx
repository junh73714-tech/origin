import { Button, Input, Space } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { useState, type KeyboardEvent } from 'react';

interface ChatComposerProps {
  disabled: boolean;
  streaming: boolean;
  onSend: (question: string) => void;
  onStop: () => void;
}

/** 问题输入框：Enter 发送，Shift+Enter 换行；生成中显示停止按钮 */
export function ChatComposer({ disabled, streaming, onSend, onStop }: ChatComposerProps) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text || disabled || streaming) return;
    onSend(text);
    setValue('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
      <Input.TextArea
        aria-label="问题输入框"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="请输入问题，Enter 发送，Shift+Enter 换行"
        autoSize={{ minRows: 1, maxRows: 5 }}
        disabled={disabled}
      />
      <Space>
        {streaming ? (
          <Button danger onClick={onStop}>
            停止生成
          </Button>
        ) : (
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={submit}
            disabled={disabled || !value.trim()}
          >
            发送
          </Button>
        )}
      </Space>
    </div>
  );
}
