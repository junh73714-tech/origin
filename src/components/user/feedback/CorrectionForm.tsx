import { Button, Form, Input, Modal } from 'antd';
import { useState } from 'react';

interface CorrectionFormProps {
  open: boolean;
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (text: string) => void;
}

/** 纠错反馈表单 */
export function CorrectionForm({ open, submitting, onCancel, onSubmit }: CorrectionFormProps) {
  const [text, setText] = useState('');

  const handleOk = () => {
    if (!text.trim()) return;
    onSubmit(text.trim());
    setText('');
  };

  return (
    <Modal
      title="提交纠错"
      open={open}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={submitting}
          disabled={!text.trim()}
          onClick={handleOk}
        >
          提交
        </Button>,
      ]}
    >
      <Form layout="vertical">
        <Form.Item label="请描述答案中的问题或正确信息">
          <Input.TextArea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="例如：该功能的入口已变更为……"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
